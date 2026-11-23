import pandas as pd

from insight_utils import (
    find_business_columns,
    parse_dates,
    period_labels,
    round_or_none,
    safe_pct_change,
)

WARNING_PCT = 15.0
CRITICAL_PCT = 30.0
MARGIN_WARNING_PP = 5.0
MARGIN_CRITICAL_PP = 10.0

KPI_LABELS = {
    "total_sales": "Total Sales",
    "total_profit": "Total Profit",
    "total_quantity": "Total Quantity",
    "order_count": "Order Count",
    "avg_order_value": "Average Order Value",
    "profit_margin": "Profit Margin",
}


def _period_kpis(frame, columns):
    sales = (
        pd.to_numeric(frame[columns["sales"]], errors="coerce")
        if columns["sales"] else None
    )
    profit = (
        pd.to_numeric(frame[columns["profit"]], errors="coerce")
        if columns["profit"] else None
    )
    quantity = (
        pd.to_numeric(frame[columns["quantity"]], errors="coerce")
        if columns["quantity"] else None
    )

    kpis = {"order_count": float(len(frame))}

    if sales is not None:
        kpis["total_sales"] = float(sales.sum())
        if len(frame) > 0:
            kpis["avg_order_value"] = float(sales.sum()) / len(frame)

    if profit is not None:
        kpis["total_profit"] = float(profit.sum())

    if sales is not None and profit is not None:
        total_sales = float(sales.sum())
        if total_sales > 0:
            kpis["profit_margin"] = float(profit.sum()) / total_sales * 100

    return kpis


def _make_alert(kpi, current, previous, current_period, previous_period,
                is_margin=False):
    change = current - previous

    if is_margin:
        change_pct = None
        magnitude = abs(change)
        severity = (
            "critical" if magnitude >= MARGIN_CRITICAL_PP
            else "warning" if magnitude >= MARGIN_WARNING_PP
            else None
        )
        unit = "percentage points"
    else:
        change_pct = safe_pct_change(current, previous)
        magnitude = abs(change_pct) if change_pct is not None else None
        severity = None

        if magnitude is not None:
            severity = (
                "critical" if magnitude >= CRITICAL_PCT
                else "warning" if magnitude >= WARNING_PCT
                else None
            )
        elif previous == 0 and current != 0:
            severity = "warning"

        unit = "%"

    if severity is None:
        return None

    direction = "increase" if change > 0 else "decrease"
    label = KPI_LABELS.get(kpi, kpi)

    if is_margin:
        message = (
            f"{label} {direction}d by {abs(change):.2f} {unit} "
            f"from {previous:.2f}% to {current:.2f}%."
        )
    elif change_pct is not None:
        message = (
            f"{label} {direction}d {abs(change_pct):.2f}% "
            f"from {previous:,.2f} to {current:,.2f} "
            f"({previous_period} vs {current_period})."
        )
    else:
        message = (
            f"{label} moved from 0 to {current:,.2f}; "
            f"no previous baseline to compute a percentage."
        )

    return {
        "id": kpi,
        "kpi": kpi,
        "label": label,
        "current": round_or_none(current),
        "previous": round_or_none(previous),
        "change": round_or_none(change),
        "change_pct": change_pct,
        "is_margin": is_margin,
        "direction": direction,
        "severity": severity,
        "current_period": current_period,
        "previous_period": previous_period,
        "message": message,
    }


def _baseline_alerts(kpis, columns, df):
    alerts = []

    if "total_profit" in kpis and kpis["total_profit"] < 0:
        alerts.append({
            "id": "negative_profit",
            "kpi": "total_profit",
            "label": "Total Profit",
            "current": round_or_none(kpis["total_profit"]),
            "previous": None,
            "change": None,
            "change_pct": None,
            "is_margin": False,
            "direction": "decrease",
            "severity": "critical",
            "current_period": None,
            "previous_period": None,
            "message": (
                f"Total profit is negative "
                f"({kpis['total_profit']:,.2f}). "
                f"This is a baseline check, not a period comparison."
            ),
        })

    if (
        "profit_margin" in kpis
        and 0 <= kpis["profit_margin"] < MARGIN_WARNING_PP
    ):
        alerts.append({
            "id": "low_margin",
            "kpi": "profit_margin",
            "label": "Profit Margin",
            "current": round_or_none(kpis["profit_margin"]),
            "previous": None,
            "change": None,
            "change_pct": None,
            "is_margin": True,
            "direction": "decrease",
            "severity": "warning",
            "current_period": None,
            "previous_period": None,
            "message": (
                f"Profit margin is low ({kpis['profit_margin']:.2f}%). "
                f"This is a baseline check, not a period comparison."
            ),
        })

    if columns["sales"]:
        sales = pd.to_numeric(df[columns["sales"]], errors="coerce")
        negative_count = int((sales < 0).sum())

        if negative_count > 0:
            alerts.append({
                "id": "negative_sales_records",
                "kpi": "total_sales",
                "label": "Negative Sales Records",
                "current": negative_count,
                "previous": None,
                "change": None,
                "change_pct": None,
                "is_margin": False,
                "direction": "decrease",
                "severity": "warning",
                "current_period": None,
                "previous_period": None,
                "message": (
                    f"{negative_count} record(s) have negative sales "
                    f"values. Verify whether these are returns or "
                    f"data entry errors."
                ),
            })

    return alerts


def generate_kpi_alerts(df):
    columns = find_business_columns(df)

    if not columns["sales"] and not columns["profit"]:
        return {
            "available": False,
            "mode": None,
            "alerts": [],
            "checked_kpis": 0,
            "message": (
                "KPI alerts need a Sales, Revenue or Profit column."
            ),
        }

    dates = parse_dates(df, columns["date"])

    if dates is not None:
        labels = period_labels(dates)
        unique_labels = sorted(labels.dropna().unique())

        if len(unique_labels) >= 2:
            current_label = unique_labels[-1]
            previous_label = unique_labels[-2]

            current_kpis = _period_kpis(
                df[labels == current_label], columns
            )
            previous_kpis = _period_kpis(
                df[labels == previous_label], columns
            )

            alerts = []
            for kpi, current in current_kpis.items():
                previous = previous_kpis.get(kpi)
                if previous is None:
                    continue

                alert = _make_alert(
                    kpi,
                    float(current),
                    float(previous),
                    str(current_label),
                    str(previous_label),
                    is_margin=(kpi == "profit_margin"),
                )
                if alert:
                    alerts.append(alert)

            alerts.sort(
                key=lambda item: (
                    0 if item["severity"] == "critical" else 1,
                    -abs(item["change_pct"] or 0),
                )
            )

            return {
                "available": True,
                "mode": "period_comparison",
                "current_period": str(current_label),
                "previous_period": str(previous_label),
                "current_kpis": {
                    key: round_or_none(value)
                    for key, value in current_kpis.items()
                },
                "previous_kpis": {
                    key: round_or_none(value)
                    for key, value in previous_kpis.items()
                },
                "alerts": alerts,
                "checked_kpis": len(current_kpis),
                "message": (
                    f"{len(alerts)} significant KPI change(s) between "
                    f"{previous_label} and {current_label}."
                ),
            }

    kpis = _period_kpis(df, columns)
    alerts = _baseline_alerts(kpis, columns, df)

    return {
        "available": True,
        "mode": "baseline",
        "current_period": None,
        "previous_period": None,
        "current_kpis": {
            key: round_or_none(value)
            for key, value in kpis.items()
        },
        "previous_kpis": None,
        "alerts": alerts,
        "checked_kpis": len(kpis),
        "message": (
            "No comparable time periods were found. "
            f"{len(alerts)} baseline KPI warning(s) generated."
        ),
    }
