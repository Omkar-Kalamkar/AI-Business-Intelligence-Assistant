import math
from datetime import datetime, timezone

from insight_utils import json_safe, safe_pct_change
from kpi_alerts import KPI_LABELS


REPORT_VERSION = 1
MAX_CHART_POINTS = 12
MAX_TREND_POINTS = 24
MAX_TABLE_ROWS = 20

KPI_FORMATS = {
    "total_sales": "currency",
    "total_profit": "currency",
    "avg_order_value": "currency",
    "total_quantity": "number",
    "order_count": "number",
    "profit_margin": "percent",
}

REQUIRED_KEYS = (
    "report_version",
    "title",
    "filename",
    "generated_at",
    "executive_summary",
    "kpi_performance",
    "charts",
    "tables",
    "anomalies",
    "trends",
    "root_cause",
    "recommendations",
)


class ReportValidationError(ValueError):
    pass


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _number(value):
    if value is None or isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def _text(value, default=""):
    return default if value is None else str(value)


def _clean(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return json_safe(value)


def _has_column(summary, names):
    columns = {
        str(column).strip().lower()
        for column in _list(summary.get("columns"))
    }
    return any(name in columns for name in names)


def _metric(metrics, key, label, value, value_format):
    number = _number(value)
    if number is None:
        return
    metrics.append({
        "key": key,
        "label": label,
        "value": number,
        "format": value_format,
    })


def _executive_summary(analysis, insights, filename):
    summary = _dict(analysis.get("summary")) or _dict(
        insights.get("summary")
    )
    alerts = _dict(insights.get("kpi_alerts"))
    anomalies = _dict(insights.get("anomalies"))
    root_cause = _dict(insights.get("root_cause"))
    current_kpis = _dict(alerts.get("current_kpis"))

    records = _number(summary.get("total_records"))
    columns_count = _number(summary.get("total_columns"))
    has_sales = _has_column(summary, ("sales", "revenue"))
    has_profit = _has_column(summary, ("profit",))
    has_quantity = _has_column(summary, ("quantity",))

    lead = f"Dataset: {filename}."
    if records is not None:
        lead += f" {int(records):,} usable record(s)"
        if columns_count is not None:
            lead += f" across {int(columns_count):,} column(s)"
        lead += "."

    paragraphs = [lead]
    metric_lines = []

    if has_sales:
        sales = _number(summary.get("total_sales"))
        if sales is not None:
            metric_lines.append(f"Recorded sales total {sales:,.2f}.")

    if has_profit:
        profit = _number(summary.get("total_profit"))
        if profit is not None:
            metric_lines.append(f"Recorded profit total {profit:,.2f}.")

    margin = _number(current_kpis.get("profit_margin"))
    if margin is not None:
        metric_lines.append(f"Overall profit margin is {margin:,.2f}%.")

    if has_quantity:
        quantity = _number(summary.get("total_quantity"))
        if quantity is not None:
            metric_lines.append(f"Total quantity recorded is {quantity:,.0f}.")

    if metric_lines:
        paragraphs.append(" ".join(metric_lines))
    else:
        paragraphs.append(
            "No numeric sales, profit or quantity fields were available "
            "in this dataset."
        )

    for narrative in (
        root_cause.get("summary"),
        alerts.get("message"),
        anomalies.get("message"),
    ):
        if narrative:
            paragraphs.append(_text(narrative))

    metrics = []
    if has_sales:
        _metric(metrics, "total_sales", "Total sales",
                summary.get("total_sales"), "currency")
    if has_profit:
        _metric(metrics, "total_profit", "Total profit",
                summary.get("total_profit"), "currency")
    _metric(metrics, "profit_margin", "Profit margin",
            current_kpis.get("profit_margin"), "percent")
    if has_quantity:
        _metric(metrics, "total_quantity", "Total quantity",
                summary.get("total_quantity"), "number")
    _metric(metrics, "total_records", "Records",
            summary.get("total_records"), "number")
    _metric(metrics, "missing_values", "Missing values",
            summary.get("missing_values"), "number")

    highlights = []
    for item in _list(analysis.get("insights"))[:6]:
        if isinstance(item, str) and item.strip():
            highlights.append(item.strip())

    for alert in _list(alerts.get("alerts"))[:3]:
        if not isinstance(alert, dict):
            continue
        message = _text(alert.get("message")).strip()
        if message:
            highlights.append(message)

    top_mover = _dict(root_cause.get("top_mover"))
    change = _number(top_mover.get("change"))
    if top_mover.get("name") and change is not None:
        highlights.append(
            f"Largest mover: {top_mover['name']} "
            f"({top_mover.get('dimension', 'dimension')}) with a change "
            f"of {change:+,.2f}."
        )

    if not highlights:
        highlights.append(
            "No specific business highlights were found in the "
            "available data."
        )

    change_pct = _number(root_cause.get("total_change_pct"))
    if change_pct is not None:
        direction = "grew" if change_pct >= 0 else "declined"
        headline = f"Sales {direction} {abs(change_pct):.2f}% between periods"
    else:
        headline = "Business performance overview"

    return {
        "headline": headline,
        "paragraphs": paragraphs,
        "metrics": metrics,
        "highlights": highlights[:8],
    }


def _kpi_performance(insights):
    alerts = _dict(insights.get("kpi_alerts"))
    current = _dict(alerts.get("current_kpis"))
    previous = _dict(alerts.get("previous_kpis"))

    alert_by_kpi = {}
    for item in _list(alerts.get("alerts")):
        if isinstance(item, dict) and item.get("kpi"):
            alert_by_kpi.setdefault(item["kpi"], item)

    preferred = (
        "total_sales",
        "total_profit",
        "profit_margin",
        "avg_order_value",
        "total_quantity",
        "order_count",
    )
    keys = [key for key in preferred if key in current]
    keys.extend(key for key in current if key not in keys)

    kpis = []
    for key in keys:
        current_value = _number(current.get(key))
        if current_value is None:
            continue

        previous_value = _number(previous.get(key))
        alert = _dict(alert_by_kpi.get(key))
        is_margin = key == "profit_margin"

        change = _number(alert.get("change"))
        if change is None and previous_value is not None:
            change = round(current_value - previous_value, 2)

        change_pct = _number(alert.get("change_pct"))
        if change_pct is None and previous_value is not None and not is_margin:
            change_pct = safe_pct_change(current_value, previous_value)

        kpis.append({
            "key": key,
            "label": _text(alert.get("label"), KPI_LABELS.get(key, key)),
            "value": current_value,
            "current": current_value,
            "previous": previous_value,
            "change": change,
            "change_pct": change_pct,
            "format": KPI_FORMATS.get(key, "number"),
            "is_margin": is_margin,
            "status": _text(alert.get("severity"), "stable"),
            "message": _text(alert.get("message"), None),
        })

    return {
        "mode": _text(alerts.get("mode"), None),
        "current_period": _text(alerts.get("current_period"), None),
        "previous_period": _text(alerts.get("previous_period"), None),
        "message": _text(
            alerts.get("message"), "KPI performance was not available."
        ),
        "checked_kpis": len(kpis),
        "kpis": kpis,
        "alerts": _clean(_list(alerts.get("alerts"))),
    }


def _chart_points(entries, label_key, value_key, limit, extras=()):
    points = []

    for entry in _list(entries)[:limit]:
        if not isinstance(entry, dict):
            continue

        label = _text(entry.get(label_key)).strip()
        value = _number(entry.get(value_key))
        if not label or value is None:
            continue

        point = {"label": label, "value": value}
        for key in extras:
            if key in entry:
                point[key] = _clean(entry[key])
        points.append(point)

    return points


def _charts(analysis, insights):
    trends = _dict(insights.get("trends"))
    trend_points = _chart_points(
        trends.get("periods"), "period", "sales", MAX_TREND_POINTS,
        extras=("is_anomaly", "severity", "zscore"),
    )

    charts = [
        {
            "id": "product_sales",
            "title": "Sales by Product",
            "type": "bar",
            "format": "currency",
            "available": bool(_list(analysis.get("product_data"))),
            "message": ("Product sales data is not available."
                        if not _list(analysis.get("product_data")) else ""),
            "data": _chart_points(
                analysis.get("product_data"), "name", "sales",
                MAX_CHART_POINTS,
            ),
        },
        {
            "id": "region_sales",
            "title": "Sales by Region",
            "type": "pie",
            "format": "currency",
            "available": bool(_list(analysis.get("region_data"))),
            "message": ("Region sales data is not available."
                        if not _list(analysis.get("region_data")) else ""),
            "data": _chart_points(
                analysis.get("region_data"), "name", "value",
                MAX_CHART_POINTS,
            ),
        },
        {
            "id": "sales_trend",
            "title": "Sales Trend",
            "type": "line",
            "format": "currency",
            "available": bool(trend_points),
            "message": _text(
                trends.get("message"), "Sales trend data is not available."
            ),
            "reference": _number(trends.get("expected_median_sales")),
            "data": trend_points,
        },
    ]

    return charts


def _table(table_id, title, columns, rows, message=""):
    return {
        "id": table_id,
        "title": title,
        "columns": [
            {"key": key, "label": label, "format": value_format}
            for key, label, value_format in columns
        ],
        "rows": _clean(rows[:MAX_TABLE_ROWS]),
        "message": message,
    }


def _tables(report, analysis, insights):
    anomalies = _dict(insights.get("anomalies"))
    trends = _dict(insights.get("trends"))
    root_cause = _dict(insights.get("root_cause"))
    recommendations = _list(insights.get("recommendations"))
    kpis = report["kpi_performance"]["kpis"]

    kpi_rows = []
    for kpi in kpis:
        kpi_rows.append({
            "label": kpi["label"],
            "current": kpi["current"],
            "previous": kpi["previous"],
            "change": kpi["change"],
            "change_pct": kpi["change_pct"],
            "status": kpi["status"],
            "format": kpi["format"],
        })

    tables = [
        _table(
            "executive_metrics",
            "Executive Metrics",
            (("label", "Metric", "text"), ("value", "Value", "auto")),
            report["executive_summary"]["metrics"],
            "No executive metrics were available.",
        ),
        _table(
            "kpi_performance",
            "KPI Performance",
            (
                ("label", "KPI", "text"),
                ("current", "Current", "auto"),
                ("previous", "Previous", "auto"),
                ("change", "Change", "auto"),
                ("change_pct", "Change %", "percent"),
                ("status", "Status", "text"),
            ),
            kpi_rows,
            "No KPI figures were available.",
        ),
    ]

    anomaly_rows = []
    for item in _list(anomalies.get("anomalies")):
        if not isinstance(item, dict):
            continue
        flagged = ", ".join(
            f"{flag.get('column')}={flag.get('value')}"
            for flag in _list(item.get("flagged_columns"))[:3]
            if isinstance(flag, dict)
        )
        anomaly_rows.append({
            "row": item.get("row_index"),
            "severity": item.get("severity"),
            "zscore": item.get("max_zscore"),
            "method": item.get("detected_by"),
            "flagged": flagged or "multivariate",
        })

    tables.append(_table(
        "anomalies",
        "Anomaly Detection",
        (
            ("row", "Row", "text"),
            ("severity", "Severity", "text"),
            ("zscore", "Z-score", "number"),
            ("method", "Detected by", "text"),
            ("flagged", "Flagged values", "text"),
        ),
        anomaly_rows,
        _text(anomalies.get("message"), "No anomaly results were available."),
    ))

    trend_rows = []
    for item in _list(trends.get("periods")):
        if not isinstance(item, dict):
            continue
        trend_rows.append({
            "period": item.get("period"),
            "sales": item.get("sales"),
            "zscore": item.get("zscore"),
            "severity": item.get("severity") or "normal",
            "deviation_pct": item.get("deviation_pct"),
        })

    tables.append(_table(
        "trend_anomalies",
        "Sales Trend Anomalies",
        (
            ("period", "Period", "text"),
            ("sales", "Sales", "currency"),
            ("zscore", "Z-score", "number"),
            ("severity", "Severity", "text"),
            ("deviation_pct", "Deviation %", "percent"),
        ),
        trend_rows,
        _text(trends.get("message"), "No trend results were available."),
    ))

    for breakdown in _list(root_cause.get("dimensions"))[:2]:
        if not isinstance(breakdown, dict):
            continue
        dimension = _text(breakdown.get("dimension"), "dimension")
        contributor_rows = []
        for item in _list(breakdown.get("contributors")):
            if isinstance(item, dict):
                contributor_rows.append({
                    "name": item.get("name"),
                    "current": item.get("current"),
                    "previous": item.get("previous"),
                    "change": item.get("change"),
                    "contribution_pct": item.get("contribution_pct"),
                })
        table_id = f"root_cause_{dimension}".replace(" ", "_").lower()
        tables.append(_table(
            table_id,
            f"Root Cause: {dimension}",
            (
                ("name", "Item", "text"),
                ("current", "Current", "currency"),
                ("previous", "Previous", "currency"),
                ("change", "Change", "currency"),
                ("contribution_pct", "Contribution %", "percent"),
            ),
            contributor_rows,
            "No contributor breakdown was available.",
        ))

    recommendation_rows = []
    for item in recommendations:
        if isinstance(item, dict):
            recommendation_rows.append({
                "priority": item.get("priority"),
                "title": item.get("title"),
                "recommendation": item.get("recommendation"),
                "reason": item.get("reason"),
            })
        else:
            recommendation_rows.append({
                "priority": "",
                "title": "Recommendation",
                "recommendation": _text(item),
                "reason": "",
            })

    tables.append(_table(
        "recommendations",
        "Business Recommendations",
        (
            ("priority", "Priority", "text"),
            ("title", "Title", "text"),
            ("recommendation", "Recommendation", "text"),
            ("reason", "Why", "text"),
        ),
        recommendation_rows,
        "No recommendations were generated.",
    ))

    summary = _dict(analysis.get("summary"))
    quality_rows = [
        {"metric": "Total records", "value": summary.get("total_records")},
        {"metric": "Total columns", "value": summary.get("total_columns")},
        {"metric": "Missing values", "value": summary.get("missing_values")},
        {
            "metric": "Duplicate records",
            "value": summary.get("duplicate_records"),
        },
    ]
    tables.append(_table(
        "data_quality",
        "Data Quality",
        (("metric", "Metric", "text"), ("value", "Value", "number")),
        quality_rows,
    ))

    return tables


def build_report_payload(analysis, insights, filename=None, dataset_id=None,
                         title=None, notes=None, generated_at=None):
    analysis = _dict(analysis)
    insights = _dict(insights)
    filename = _text(filename or insights.get("filename"), "Unknown dataset")
    title = _text(title, "").strip() or "Business Intelligence Report"
    notes = _text(notes, "").strip()
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    payload = {
        "report_version": REPORT_VERSION,
        "title": title,
        "filename": filename,
        "dataset_id": _text(dataset_id or insights.get("dataset_id"), None),
        "generated_at": generated_at,
        "notes": notes,
        "source_insight_id": insights.get("insight_id"),
    }

    payload["executive_summary"] = _executive_summary(
        analysis, insights, filename
    )
    payload["kpi_performance"] = _kpi_performance(insights)
    payload["charts"] = _charts(analysis, insights)
    payload["anomalies"] = _clean(_dict(insights.get("anomalies")))
    payload["trends"] = _clean(_dict(insights.get("trends")))
    payload["root_cause"] = _clean(_dict(insights.get("root_cause")))
    payload["recommendations"] = _clean(_list(insights.get("recommendations")))
    payload["tables"] = _tables(payload, analysis, insights)

    warnings = []
    summary = _dict(analysis.get("summary"))
    missing = _number(summary.get("missing_values"))
    if missing:
        warnings.append(
            f"{int(missing)} missing value(s) were present in the data."
        )
    for chart in payload["charts"]:
        if not chart["data"]:
            warnings.append(f"{chart['title']} could not be charted.")

    payload["warnings"] = warnings
    payload = _clean(payload)
    validate_report_payload(payload)
    return payload


def _check_finite(value, path="payload"):
    if isinstance(value, float) and not math.isfinite(value):
        raise ReportValidationError(f"Non-finite number at {path}.")

    if isinstance(value, dict):
        for key, item in value.items():
            _check_finite(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _check_finite(item, f"{path}[{index}]")


def validate_report_payload(payload):
    if not isinstance(payload, dict):
        raise ReportValidationError("Report payload must be an object.")

    for key in REQUIRED_KEYS:
        if key not in payload:
            raise ReportValidationError(f"Missing report field: {key}.")

    if payload["report_version"] != REPORT_VERSION:
        raise ReportValidationError("Unsupported report version.")

    for key in ("title", "filename", "generated_at"):
        if not isinstance(payload[key], str):
            raise ReportValidationError(f"Report field {key} must be text.")

    summary = payload["executive_summary"]
    if not isinstance(summary, dict):
        raise ReportValidationError("Executive summary must be an object.")
    for key in ("headline", "paragraphs", "metrics", "highlights"):
        if key not in summary:
            raise ReportValidationError(f"Executive summary needs {key}.")

    performance = payload["kpi_performance"]
    if not isinstance(performance, dict) or not isinstance(
        performance.get("kpis"), list
    ):
        raise ReportValidationError("KPI performance data is invalid.")

    for kpi in performance["kpis"]:
        if not isinstance(kpi, dict) or not kpi.get("key"):
            raise ReportValidationError("A KPI entry is invalid.")

    if not isinstance(payload["charts"], list):
        raise ReportValidationError("Charts must be a list.")

    for chart in payload["charts"]:
        if not isinstance(chart, dict):
            raise ReportValidationError("A chart entry is invalid.")
        if chart.get("type") not in ("bar", "line", "pie"):
            raise ReportValidationError("Unsupported chart type.")
        if not isinstance(chart.get("data"), list):
            raise ReportValidationError("Chart data must be a list.")
        for point in chart["data"]:
            if not isinstance(point, dict):
                raise ReportValidationError("A chart point is invalid.")
            if not isinstance(point.get("label"), str):
                raise ReportValidationError("A chart point label is invalid.")
            if _number(point.get("value")) is None:
                raise ReportValidationError("A chart point value is invalid.")

    if not isinstance(payload["tables"], list):
        raise ReportValidationError("Tables must be a list.")

    for table in payload["tables"]:
        if not isinstance(table, dict):
            raise ReportValidationError("A table entry is invalid.")
        if not isinstance(table.get("columns"), list) or not isinstance(
            table.get("rows"), list
        ):
            raise ReportValidationError("Table columns and rows are invalid.")
        for column in table["columns"]:
            if not isinstance(column, dict) or not column.get("key"):
                raise ReportValidationError("A table column is invalid.")

    _check_finite(payload)
    return True
