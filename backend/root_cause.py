import pandas as pd

from insight_utils import (
    DIMENSION_COLUMN_NAMES,
    find_business_columns,
    parse_dates,
    period_labels,
    round_or_none,
    safe_pct_change,
)

MAX_CONTRIBUTORS = 10


def _dimension_breakdown(current_df, previous_df, dimension_col, sales_col, total_change):
    current_totals = (
        current_df.groupby(dimension_col)[sales_col].sum()
        if len(current_df) else pd.Series(dtype="float64")
    )
    previous_totals = (
        previous_df.groupby(dimension_col)[sales_col].sum()
        if len(previous_df) else pd.Series(dtype="float64")
    )

    names = sorted(
        set(current_totals.index.astype(str))
        | set(previous_totals.index.astype(str))
    )

    contributors = []

    for name in names:
        current_value = float(
            current_totals[current_totals.index.astype(str) == name].sum()
        )
        previous_value = float(
            previous_totals[previous_totals.index.astype(str) == name].sum()
        )
        change = current_value - previous_value

        contribution_pct = None
        if total_change:
            contribution_pct = round(change / total_change * 100, 2)

        contributors.append({
            "name": name,
            "current": round(current_value, 2),
            "previous": round(previous_value, 2),
            "change": round(change, 2),
            "change_pct": safe_pct_change(current_value, previous_value),
            "contribution_pct": contribution_pct,
        })

    contributors.sort(key=lambda item: abs(item["change"]), reverse=True)
    return contributors[:MAX_CONTRIBUTORS]


def _overall_contribution(df, dimension_col, sales_col):
    grouped = df.groupby(dimension_col)[sales_col].sum()
    total = float(grouped.sum())

    contributors = []
    for name, value in grouped.items():
        value = float(value)
        contributors.append({
            "name": str(name),
            "current": round(value, 2),
            "previous": None,
            "change": None,
            "change_pct": None,
            "contribution_pct": (
                round(value / total * 100, 2) if total else None
            ),
        })

    contributors.sort(key=lambda item: item["current"], reverse=True)
    return contributors[:MAX_CONTRIBUTORS]


def analyze_root_cause(df, trends=None):
    columns = find_business_columns(df)
    sales_col = columns["sales"]
    date_col = columns["date"]

    dimensions = [
        (name, columns[name])
        for name in DIMENSION_COLUMN_NAMES
        if columns[name]
    ]

    if not sales_col:
        return {
            "available": False,
            "message": (
                "Root cause analysis needs a Sales or Revenue column."
            ),
            "dimensions": [],
        }

    sales = pd.to_numeric(df[sales_col], errors="coerce")
    df = df.copy()
    df[sales_col] = sales
    dates = parse_dates(df, date_col)

    if dates is not None:
        labels = period_labels(dates)
        unique_labels = sorted(labels.dropna().unique())

        if len(unique_labels) >= 2:
            current_label = unique_labels[-1]
            previous_label = unique_labels[-2]

            current_mask = labels == current_label
            previous_mask = labels == previous_label

            current_total = float(sales[current_mask].sum())
            previous_total = float(sales[previous_mask].sum())
            total_change = current_total - previous_total

            breakdowns = []
            for name, dimension_col in dimensions:
                contributors = _dimension_breakdown(
                    df[current_mask],
                    df[previous_mask],
                    dimension_col,
                    sales_col,
                    total_change,
                )
                if contributors:
                    breakdowns.append({
                        "dimension": name,
                        "contributors": contributors,
                    })

            direction = "increased" if total_change > 0 else "decreased"
            summary = (
                f"Total sales {direction} from {previous_total:,.2f} "
                f"({previous_label}) to {current_total:,.2f} "
                f"({current_label}), a change of {total_change:+,.2f}. "
                "Figures below show how much each item contributed "
                "to this change; they describe contributions, "
                "not proven causes."
            )

            top_mover = None
            if breakdowns and breakdowns[0]["contributors"]:
                top = breakdowns[0]["contributors"][0]
                top_mover = {
                    "dimension": breakdowns[0]["dimension"],
                    **top,
                }
                summary += (
                    f" Largest mover: {top['name']} "
                    f"({breakdowns[0]['dimension']}) "
                    f"with a change of {top['change']:+,.2f}."
                )

            if trends and trends.get("available"):
                last_period = trends["periods"][-1]
                if last_period["is_anomaly"]:
                    summary += (
                        f" The latest period ({current_label}) was also "
                        f"flagged as an unusual sales period."
                    )

            return {
                "available": True,
                "mode": "period_comparison",
                "current_period": str(current_label),
                "previous_period": str(previous_label),
                "current_total": round(current_total, 2),
                "previous_total": round(previous_total, 2),
                "total_change": round(total_change, 2),
                "total_change_pct": safe_pct_change(
                    current_total, previous_total
                ),
                "dimensions": breakdowns,
                "top_mover": top_mover,
                "summary": summary,
            }

    if not dimensions:
        return {
            "available": False,
            "message": (
                "Root cause analysis needs a Product, Category or "
                "Region column, or at least two dated periods."
            ),
            "dimensions": [],
        }

    breakdowns = []
    for name, dimension_col in dimensions:
        contributors = _overall_contribution(df, dimension_col, sales_col)
        if contributors:
            breakdowns.append({
                "dimension": name,
                "contributors": contributors,
            })

    total_sales = float(sales.sum())

    return {
        "available": True,
        "mode": "contribution",
        "current_period": None,
        "previous_period": None,
        "current_total": round_or_none(total_sales),
        "previous_total": None,
        "total_change": None,
        "total_change_pct": None,
        "dimensions": breakdowns,
        "top_mover": None,
        "summary": (
            f"No usable date column with multiple periods was found, "
            f"so period-over-period comparison is not possible. "
            f"Total sales are {total_sales:,.2f}. The breakdown below "
            f"shows each item's share of total sales."
        ),
    }
