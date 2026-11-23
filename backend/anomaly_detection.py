import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from insight_utils import (
    SEVERITY_RANK,
    find_business_columns,
    json_safe,
    numeric_columns,
    numeric_frame,
    parse_dates,
    period_labels,
    robust_zscores,
    round_or_none,
    severity_from_z,
)

MIN_ROWS = 8
Z_THRESHOLD = 3.5
TREND_Z_THRESHOLD = 3.0
MAX_RESULTS = 100


def detect_anomalies(df, max_results=MAX_RESULTS):
    columns = numeric_columns(df)
    usable = []

    frame = numeric_frame(df, columns)

    for column in columns:
        values = frame[column].dropna()
        if len(values) >= MIN_ROWS and values.nunique() > 1:
            usable.append(column)

    if len(df) < MIN_ROWS or not usable:
        return {
            "available": False,
            "message": (
                "Anomaly detection needs at least "
                f"{MIN_ROWS} rows and one varying numeric column."
            ),
            "numeric_columns": usable,
            "total_records": int(len(df)),
            "anomaly_count": 0,
            "severity_counts": {},
            "anomalies": [],
        }

    frame = frame[usable]
    imputed = frame.fillna(frame.median())

    zscores = pd.DataFrame(
        {column: robust_zscores(frame[column]) for column in usable}
    )

    forest = IsolationForest(
        n_estimators=200,
        contamination=0.03,
        random_state=42,
    )
    forest.fit(imputed.to_numpy())

    if_flags = forest.predict(imputed.to_numpy()) == -1
    if_scores = -forest.score_samples(imputed.to_numpy())

    anomalies = []

    for position in range(len(df)):
        row_z = zscores.iloc[position]
        max_z = float(row_z.abs().max())
        flagged = max_z >= Z_THRESHOLD
        isolated = bool(if_flags[position]) and max_z >= 2.0

        if not flagged and not isolated:
            continue

        if flagged:
            severity = severity_from_z(max_z)
        else:
            severity = "low"

        flagged_columns = []

        for column in usable:
            z = float(row_z[column])
            value = frame[column].iloc[position]

            if abs(z) < Z_THRESHOLD:
                continue

            clean = frame[column].dropna()
            q1 = float(clean.quantile(0.25))
            q3 = float(clean.quantile(0.75))
            iqr = q3 - q1

            flagged_columns.append({
                "column": column,
                "value": json_safe(value),
                "zscore": round(z, 2),
                "expected_median": round_or_none(clean.median()),
                "lower_bound": round_or_none(q1 - 1.5 * iqr),
                "upper_bound": round_or_none(q3 + 1.5 * iqr),
            })

        row_index = df.index[position]
        record = {
            str(column): json_safe(df[column].iloc[position])
            for column in df.columns
        }

        anomalies.append({
            "row_index": int(row_index) if isinstance(row_index, (int, np.integer)) else str(row_index),
            "severity": severity,
            "max_zscore": round(max_z, 2),
            "isolation_score": round(float(if_scores[position]), 4),
            "detected_by": (
                "statistical+isolation_forest" if flagged and isolated
                else "statistical" if flagged
                else "isolation_forest"
            ),
            "flagged_columns": flagged_columns,
            "record": record,
        })

    anomalies.sort(
        key=lambda item: (
            SEVERITY_RANK[item["severity"]],
            -item["max_zscore"],
        )
    )

    total_count = len(anomalies)
    anomalies = anomalies[:max_results]

    severity_counts = {}
    for item in anomalies:
        severity_counts[item["severity"]] = (
            severity_counts.get(item["severity"], 0) + 1
        )

    return {
        "available": True,
        "method": "robust_zscore+isolation_forest",
        "numeric_columns": usable,
        "total_records": int(len(df)),
        "anomaly_count": total_count,
        "returned_count": len(anomalies),
        "severity_counts": severity_counts,
        "anomalies": anomalies,
        "message": (
            f"{total_count} unusual record(s) detected out of "
            f"{len(df)} rows."
        ),
    }


def detect_trend_anomalies(df):
    columns = find_business_columns(df)
    sales_col = columns["sales"]
    date_col = columns["date"]

    if not sales_col or not date_col:
        return {
            "available": False,
            "message": (
                "Trend analysis needs a date column and a "
                "Sales or Revenue column."
            ),
            "periods": [],
            "anomaly_count": 0,
        }

    dates = parse_dates(df, date_col)

    if dates is None:
        return {
            "available": False,
            "message": "The date column could not be parsed.",
            "periods": [],
            "anomaly_count": 0,
        }

    sales = pd.to_numeric(df[sales_col], errors="coerce")
    profit_col = columns["profit"]
    profit = (
        pd.to_numeric(df[profit_col], errors="coerce")
        if profit_col else None
    )

    working = pd.DataFrame({
        "period": period_labels(dates),
        "sales": sales,
    })
    if profit is not None:
        working["profit"] = profit

    grouped = working.groupby("period", sort=True).sum(min_count=1)
    grouped = grouped.dropna(subset=["sales"])

    if len(grouped) < 6:
        return {
            "available": False,
            "message": (
                "Trend analysis needs at least 6 distinct periods; "
                f"found {len(grouped)}."
            ),
            "periods": [],
            "anomaly_count": 0,
        }

    zscores = robust_zscores(grouped["sales"])
    median_sales = float(grouped["sales"].median())

    periods = []
    anomaly_count = 0

    for i, (label, row) in enumerate(grouped.iterrows()):
        z = float(zscores.iloc[i])
        is_anomaly = abs(z) >= TREND_Z_THRESHOLD
        sales_value = float(row["sales"])

        deviation_pct = None
        if median_sales != 0:
            deviation_pct = round(
                (sales_value - median_sales) / abs(median_sales) * 100, 2
            )

        entry = {
            "period": str(label),
            "sales": round(sales_value, 2),
            "zscore": round(z, 2),
            "is_anomaly": is_anomaly,
            "severity": (
                severity_from_z(z, medium=3.0, high=4.0, critical=5.0)
                if is_anomaly else None
            ),
            "deviation_pct": deviation_pct,
            "direction": (
                "above" if sales_value > median_sales else "below"
            ),
        }

        if "profit" in grouped.columns:
            entry["profit"] = round_or_none(row["profit"])

        if is_anomaly:
            anomaly_count += 1

        periods.append(entry)

    return {
        "available": True,
        "sales_column": sales_col,
        "expected_median_sales": round_or_none(median_sales),
        "period_count": len(periods),
        "anomaly_count": anomaly_count,
        "periods": periods,
        "message": (
            f"{anomaly_count} unusual sales period(s) detected "
            f"across {len(periods)} periods."
        ),
    }
