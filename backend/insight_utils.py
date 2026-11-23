import math
from datetime import date, datetime

import numpy as np
import pandas as pd


DATE_COLUMN_NAMES = [
    "date", "order date", "order_date", "orderdate",
    "transaction date", "transaction_date", "sale date",
    "sale_date", "sales date", "invoice date", "invoice_date",
    "timestamp", "time", "day", "month", "period",
]

DIMENSION_COLUMN_NAMES = ["product", "category", "region"]


def column_lookup(df):
    return {
        str(column).strip().lower(): column
        for column in df.columns
    }


def find_business_columns(df):
    lookup = column_lookup(df)

    date_col = None
    for name in DATE_COLUMN_NAMES:
        if name in lookup:
            date_col = lookup[name]
            break

    return {
        "sales": lookup.get("sales") or lookup.get("revenue"),
        "profit": lookup.get("profit"),
        "quantity": lookup.get("quantity"),
        "product": lookup.get("product"),
        "category": lookup.get("category"),
        "region": lookup.get("region"),
        "date": date_col,
    }


def numeric_columns(df):
    numeric = df.select_dtypes(include="number").columns.tolist()

    for column in df.columns:
        if column in numeric:
            continue

        if df[column].dtype == object:
            converted = pd.to_numeric(df[column], errors="coerce")
            non_null = df[column].notna().sum()

            if non_null > 0 and converted.notna().sum() >= 0.6 * non_null:
                numeric.append(column)

    return numeric


def numeric_frame(df, columns):
    frame = pd.DataFrame(index=df.index)

    for column in columns:
        frame[column] = pd.to_numeric(df[column], errors="coerce")

    return frame


def parse_dates(df, date_col):
    if date_col is None:
        return None

    try:
        dates = pd.to_datetime(
            df[date_col], errors="coerce", format="mixed"
        )
    except (TypeError, ValueError):
        return None

    if dates.notna().sum() < max(2, int(0.8 * len(df))):
        return None

    return dates


def choose_period_freq(dates):
    span_days = (dates.max() - dates.min()).days

    if span_days <= 92:
        return "D", "%Y-%m-%d", "day"
    if span_days <= 730:
        return "W", "%Y-%m-%d", "week"
    return "M", "%Y-%m", "month"


def period_labels(dates, drop_partial=True):
    freq, label_format, _ = choose_period_freq(dates)
    buckets = dates.dt.to_period(freq)
    labels = buckets.dt.to_timestamp().dt.strftime(label_format)

    if drop_partial and freq in ("W", "M") and buckets.notna().any():
        last_bucket = buckets.max()
        bucket_end = last_bucket.end_time.normalize()

        if dates.max().normalize() < bucket_end:
            labels = labels.where(buckets != last_bucket, other=None)

    return labels


def robust_zscores(values):
    series = pd.Series(values, dtype="float64").reset_index(drop=True)
    clean = series.dropna()

    if len(clean) < 3:
        return pd.Series(0.0, index=series.index)

    median = float(clean.median())
    mad = float((clean - median).abs().median())

    if mad > 0:
        scale = mad / 0.6745
    else:
        mean_ad = float((clean - median).abs().mean())
        scale = 1.253314 * mean_ad

    if not scale or math.isnan(scale):
        return pd.Series(0.0, index=series.index)

    return ((series - median) / scale).fillna(0.0)


def severity_from_z(z, medium=3.5, high=4.5, critical=6.0):
    z = abs(float(z))

    if z >= critical:
        return "critical"
    if z >= high:
        return "high"
    if z >= medium:
        return "medium"
    return "low"


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, str):
        return value

    return str(value)


def safe_pct_change(current, previous):
    if previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)


def round_or_none(value, digits=2):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)
