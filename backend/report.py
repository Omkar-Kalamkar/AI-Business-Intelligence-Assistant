import io
import json
import math
import re

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


MAX_DETAIL_ROWS = 10
MAX_TREND_ROWS = 15
MAX_ALERTS = 10
MAX_TEXT = 400
CHART_COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981", "#ec4899"]


def _ascii_filename(filename):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(filename or ""))
    cleaned = cleaned.strip("._") or "report"
    return cleaned[:80] if cleaned.lower().endswith(".pdf") else cleaned[:76] + ".pdf"


def _stringify(value, limit=MAX_TEXT):
    if value is None:
        return "-"
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, default=str, ensure_ascii=True)
    else:
        text = str(value)

    text = text.encode("latin-1", "replace").decode("latin-1")
    text = " ".join(text.split())

    if len(text) > limit:
        return text[: limit - 3] + "..."

    return text


def _paragraph(text, style, limit=MAX_TEXT):
    return Paragraph(escape(_stringify(text, limit)), style)


def _table(headers, rows, styles, widths=None):
    data = [[_paragraph(header, styles["header"]) for header in headers]]
    for row in rows:
        data.append([_paragraph(value, styles["cell"]) for value in row])

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#312e81")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white, colors.HexColor("#f8fafc")
        ]),
    ]))
    return table


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name="ReportTitle",
        parent=base["Title"],
        fontSize=20,
        leading=24,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))
    base.add(ParagraphStyle(
        name="ReportHeading",
        parent=base["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#3730a3"),
    ))
    base.add(ParagraphStyle(
        name="ReportBody",
        parent=base["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        name="ReportHeaderCell",
        parent=base["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#312e81"),
    ))
    base.add(ParagraphStyle(
        name="ReportCell",
        parent=base["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=0,
    ))

    return {
        "title": base["ReportTitle"],
        "heading": base["ReportHeading"],
        "body": base["ReportBody"],
        "header": base["ReportHeaderCell"],
        "cell": base["ReportCell"],
    }


def _summary_section(story, payload, styles):
    summary = payload.get("summary") or {}
    story.append(_paragraph("Business Intelligence Report", styles["title"]))
    story.append(_paragraph(
        f"Dataset: {payload.get('filename') or 'Unknown'}", styles["body"]
    ))
    story.append(_paragraph(
        f"Generated: {payload.get('generated_at') or 'Unknown'}",
        styles["body"],
    ))
    story.append(Spacer(1, 6))

    story.append(_paragraph("Executive Summary", styles["heading"]))
    rows = [
        ["Total records", summary.get("total_records", "-")],
        ["Total columns", summary.get("total_columns", "-")],
        ["Total sales", summary.get("total_sales", "-")],
        ["Total profit", summary.get("total_profit", "-")],
        ["Total quantity", summary.get("total_quantity", "-")],
        ["Missing values", summary.get("missing_values", "-")],
        ["Duplicate records", summary.get("duplicate_records", "-")],
    ]
    story.append(_table(["Metric", "Value"], rows, styles, [60 * mm, 110 * mm]))

    for insight in (summary.get("insights") or [])[:5]:
        story.append(_paragraph(f"- {insight}", styles["body"]))


def _anomaly_section(story, payload, styles):
    anomalies = payload.get("anomalies") or {}
    story.append(_paragraph("Anomaly Detection", styles["heading"]))
    story.append(_paragraph(
        anomalies.get("message") or "Anomaly detection was not available.",
        styles["body"],
    ))

    records = anomalies.get("anomalies") or []
    if anomalies.get("available") and records:
        rows = []
        for item in records[:MAX_DETAIL_ROWS]:
            flags = ", ".join(
                f"{flag.get('column')}={flag.get('value')}"
                for flag in (item.get("flagged_columns") or [])[:3]
            )
            rows.append([
                item.get("row_index", "-"),
                item.get("severity", "-"),
                item.get("max_zscore", "-"),
                flags or "multivariate",
            ])
        story.append(_table(
            ["Row", "Severity", "Z-score", "Flagged values"],
            rows,
            styles,
            [18 * mm, 24 * mm, 22 * mm, 106 * mm],
        ))


def _trend_section(story, payload, styles):
    trends = payload.get("trends") or {}
    story.append(_paragraph("Sales Trend Anomalies", styles["heading"]))
    story.append(_paragraph(
        trends.get("message") or "Trend analysis was not available.",
        styles["body"],
    ))

    periods = trends.get("periods") or []
    if trends.get("available") and periods:
        rows = []
        for period in periods[:MAX_TREND_ROWS]:
            rows.append([
                period.get("period", "-"),
                period.get("sales", "-"),
                period.get("zscore", "-"),
                period.get("severity") or "-",
                period.get("deviation_pct", "-"),
            ])
        story.append(_table(
            ["Period", "Sales", "Z-score", "Severity", "Deviation %"],
            rows,
            styles,
            [40 * mm, 34 * mm, 25 * mm, 32 * mm, 39 * mm],
        ))


def _root_cause_section(story, payload, styles):
    root_cause = payload.get("root_cause") or {}
    story.append(_paragraph("Root Cause Analysis", styles["heading"]))
    story.append(_paragraph(
        root_cause.get("summary") or root_cause.get("message")
        or "Root cause analysis was not available.",
        styles["body"],
    ))

    for breakdown in (root_cause.get("dimensions") or [])[:2]:
        story.append(_paragraph(
            f"Dimension: {breakdown.get('dimension', '-')}",
            styles["body"],
        ))
        rows = []
        for item in (breakdown.get("contributors") or [])[:5]:
            rows.append([
                item.get("name", "-"),
                item.get("current", "-"),
                item.get("previous", "-"),
                item.get("change", "-"),
                item.get("contribution_pct", "-"),
            ])
        story.append(_table(
            ["Item", "Current", "Previous", "Change", "Contribution %"],
            rows,
            styles,
            [44 * mm, 32 * mm, 32 * mm, 32 * mm, 30 * mm],
        ))


def _alerts_section(story, payload, styles):
    alerts = payload.get("kpi_alerts") or {}
    story.append(_paragraph("KPI Alerts", styles["heading"]))
    story.append(_paragraph(
        alerts.get("message") or "KPI alerts were not available.",
        styles["body"],
    ))

    items = alerts.get("alerts") or []
    if items:
        rows = [
            [item.get("severity", "-"), item.get("label", "-"),
             item.get("message", "-")]
            for item in items[:MAX_ALERTS]
        ]
        story.append(_table(
            ["Severity", "KPI", "Message"],
            rows,
            styles,
            [24 * mm, 38 * mm, 108 * mm],
        ))


def _recommendation_section(story, payload, styles):
    recommendations = payload.get("recommendations") or []
    story.append(_paragraph("Business Recommendations", styles["heading"]))

    if not recommendations:
        story.append(_paragraph(
            "No recommendations were generated.", styles["body"]
        ))
        return

    for item in recommendations:
        if not isinstance(item, dict):
            story.append(_paragraph(f"- {item}", styles["body"]))
            continue

        story.append(_paragraph(
            f"{item.get('title', 'Recommendation')} "
            f"[{item.get('priority', '-')}]",
            styles["body"],
        ))
        story.append(_paragraph(
            item.get("recommendation", ""), styles["body"]
        ))
        story.append(_paragraph(
            f"Why: {item.get('reason', '')}", styles["body"]
        ))

        evidence = item.get("evidence") or []
        if any(not isinstance(entry, dict) for entry in evidence):
            evidence = []
        if evidence:
            rows = [
                [entry.get("label", "-"), entry.get("value", "-")]
                for entry in evidence[:5]
            ]
            story.append(_table(
                ["Evidence", "Value"], rows, styles, [80 * mm, 90 * mm]
            ))
        story.append(Spacer(1, 4))


def _finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _chart_drawing(chart):
    data = []

    for point in (chart or {}).get("data") or []:
        if not isinstance(point, dict):
            continue
        value = _finite_number(point.get("value"))
        if value is None:
            continue
        data.append((
            _stringify(point.get("label"), limit=20),
            value,
            point,
        ))

    width = 170 * mm
    height = 70 * mm
    drawing = Drawing(width, height)
    drawing.hAlign = "LEFT"
    drawing.add(Rect(
        0, 0, width, height,
        strokeColor=None, fillColor=colors.white,
    ))

    if not data:
        drawing.add(String(
            12, float(height) / 2, "No chart data available.",
            fontName="Helvetica", fontSize=9,
            fillColor=colors.HexColor("#64748b"),
        ))
        return drawing

    axis_x = 46.0
    baseline = 26.0
    plot_width = float(width) - 62.0
    plot_height = float(height) - 44.0
    values = [item[1] for item in data]
    low = min(0.0, min(values))
    high = max(0.0, max(values))
    if high == low:
        high = low + 1.0

    def y_for(value):
        return baseline + (value - low) / (high - low) * plot_height

    drawing.add(Line(
        axis_x, baseline, axis_x + plot_width, baseline,
        strokeColor=colors.HexColor("#94a3b8"), strokeWidth=0.6,
    ))
    drawing.add(Line(
        axis_x, baseline, axis_x, baseline + plot_height,
        strokeColor=colors.HexColor("#94a3b8"), strokeWidth=0.6,
    ))

    for marker in (low, high):
        drawing.add(String(
            4, y_for(marker) - 2, _stringify(round(marker, 2), limit=12),
            fontName="Helvetica", fontSize=7,
            fillColor=colors.HexColor("#64748b"),
        ))

    if (chart or {}).get("type") == "pie":
        total = sum(abs(value) for _, value, _ in data)
        if total <= 0:
            return drawing

        center_x = axis_x + plot_width * 0.3
        center_y = baseline + plot_height / 2
        radius = min(plot_height / 2 - 4, plot_width * 0.22)
        angle = 90.0
        legend_x = axis_x + plot_width * 0.58
        legend_y = baseline + plot_height - 4

        for index, (label, value, _) in enumerate(data[:8]):
            extent = abs(value) / total * 360
            if extent <= 0:
                continue
            color = colors.HexColor(
                CHART_COLORS[index % len(CHART_COLORS)]
            )
            drawing.add(Wedge(
                center_x, center_y, radius, angle, angle + extent,
                fillColor=color, strokeColor=colors.white,
                strokeWidth=1,
            ))
            if legend_y > baseline + 10:
                drawing.add(Rect(
                    legend_x, legend_y - 6, 8, 8,
                    fillColor=color, strokeColor=None,
                ))
                drawing.add(String(
                    legend_x + 12, legend_y - 6,
                    _stringify(f"{label} ({value:,.0f})", limit=34),
                    fontName="Helvetica", fontSize=7,
                    fillColor=colors.HexColor("#334155"),
                ))
                legend_y -= 12
            angle += extent
        return drawing

    tick_step = max(1, math.ceil(len(data) / 9))
    slot = plot_width / len(data)

    if (chart or {}).get("type") == "line":
        reference = _finite_number((chart or {}).get("reference"))
        if reference is not None and low <= reference <= high:
            drawing.add(Line(
                axis_x, y_for(reference),
                axis_x + plot_width, y_for(reference),
                strokeColor=colors.HexColor("#94a3b8"),
                strokeWidth=0.7, strokeDashArray=(4, 3),
            ))

        positions = [
            axis_x + slot * (index + 0.5)
            for index in range(len(data))
        ]
        for index in range(len(data) - 1):
            drawing.add(Line(
                positions[index], y_for(values[index]),
                positions[index + 1], y_for(values[index + 1]),
                strokeColor=colors.HexColor("#6366f1"), strokeWidth=1.6,
            ))

        for index, (label, value, point) in enumerate(data):
            unusual = bool(point.get("is_anomaly"))
            drawing.add(Circle(
                positions[index], y_for(value),
                3.2 if unusual else 2.2,
                fillColor=(
                    colors.HexColor("#dc2626") if unusual
                    else colors.HexColor("#6366f1")
                ),
                strokeColor=colors.white if unusual else None,
            ))
            if index % tick_step == 0:
                drawing.add(String(
                    positions[index] - 12, baseline - 12, label,
                    fontName="Helvetica", fontSize=6.5,
                    fillColor=colors.HexColor("#64748b"),
                ))
        return drawing

    bar_width = min(28.0, slot * 0.65)
    zero_line = y_for(0.0)

    for index, (label, value, _) in enumerate(data):
        bar_top = y_for(value)
        x_position = axis_x + index * slot + (slot - bar_width) / 2
        drawing.add(Rect(
            x_position, min(bar_top, zero_line),
            bar_width, max(1.5, abs(bar_top - zero_line)),
            fillColor=colors.HexColor(
                CHART_COLORS[index % len(CHART_COLORS)]
            ),
            strokeColor=None,
        ))
        if index % tick_step == 0:
            drawing.add(String(
                x_position, baseline - 12, label,
                fontName="Helvetica", fontSize=6.5,
                fillColor=colors.HexColor("#64748b"),
            ))
    return drawing


def _report_table(table, styles):
    columns = (table or {}).get("columns") or []
    if not columns:
        return _paragraph("No columns were available.", styles["body"])

    headers = [column.get("label", "-") for column in columns]
    rows = []
    for row in (table or {}).get("rows") or []:
        rows.append([
            row.get(column.get("key"), "-") if isinstance(row, dict) else "-"
            for column in columns
        ])

    width = 174 * mm / len(headers)
    return _table(headers, rows, styles, [width] * len(headers))


def _report_header(story, payload, styles):
    story.append(_paragraph(
        payload.get("title") or "Business Intelligence Report",
        styles["title"],
    ))
    story.append(_paragraph(
        f"Dataset: {payload.get('filename') or 'Unknown'}", styles["body"]
    ))
    story.append(_paragraph(
        f"Generated: {payload.get('generated_at') or 'Unknown'}",
        styles["body"],
    ))
    if payload.get("notes"):
        story.append(_paragraph(
            f"Notes: {payload['notes']}", styles["body"]
        ))
    story.append(Spacer(1, 6))


def _report_executive_section(story, payload, styles):
    summary = payload.get("executive_summary") or {}
    story.append(_paragraph("Executive Summary", styles["heading"]))
    story.append(_paragraph(
        summary.get("headline") or "Business performance overview",
        styles["body"],
    ))

    for paragraph in summary.get("paragraphs") or []:
        story.append(_paragraph(paragraph, styles["body"]))

    metrics = summary.get("metrics") or []
    if metrics:
        rows = [
            [metric.get("label", "-"), metric.get("value", "-")]
            for metric in metrics if isinstance(metric, dict)
        ]
        story.append(_table(
            ["Metric", "Value"], rows, styles, [70 * mm, 100 * mm]
        ))
    else:
        story.append(_paragraph(
            "No executive metrics were available.", styles["body"]
        ))

    highlights = summary.get("highlights") or []
    if highlights:
        story.append(_paragraph("Highlights", styles["heading"]))
        for highlight in highlights:
            story.append(_paragraph(f"- {highlight}", styles["body"]))

    warnings = payload.get("warnings") or []
    for warning in warnings:
        story.append(_paragraph(f"Note: {warning}", styles["body"]))


def _report_kpi_section(story, payload, styles):
    performance = payload.get("kpi_performance") or {}
    story.append(_paragraph("KPI Performance", styles["heading"]))
    story.append(_paragraph(
        performance.get("message") or "KPI performance was not available.",
        styles["body"],
    ))

    periods = []
    if performance.get("current_period"):
        periods.append(f"current: {performance['current_period']}")
    if performance.get("previous_period"):
        periods.append(f"previous: {performance['previous_period']}")
    if periods:
        story.append(_paragraph("; ".join(periods), styles["body"]))

    table = next(
        (item for item in payload.get("tables") or []
         if isinstance(item, dict) and item.get("id") == "kpi_performance"),
        None,
    )
    if table:
        story.append(_report_table(table, styles))


def _report_charts_section(story, payload, styles):
    story.append(_paragraph("Charts", styles["heading"]))

    for chart in payload.get("charts") or []:
        if not isinstance(chart, dict):
            continue
        story.append(_paragraph(
            chart.get("title") or "Chart", styles["heading"]
        ))
        if not chart.get("data") and chart.get("message"):
            story.append(_paragraph(chart["message"], styles["body"]))
        story.append(_chart_drawing(chart))
        story.append(Spacer(1, 8))


def _report_detection_notes(story, payload, styles):
    sections = (
        ("anomalies", "Anomaly Detection"),
        ("trends", "Sales Trend Anomalies"),
        ("root_cause", "Root Cause Analysis"),
    )

    for key, title in sections:
        section = payload.get(key) or {}
        message = section.get("summary") or section.get("message")
        if not message:
            continue
        story.append(_paragraph(title, styles["heading"]))
        story.append(_paragraph(message, styles["body"]))


def _report_tables_section(story, payload, styles):
    story.append(_paragraph("Detailed Tables", styles["heading"]))
    skip = {"kpi_performance", "executive_metrics"}

    for table in payload.get("tables") or []:
        if not isinstance(table, dict) or table.get("id") in skip:
            continue
        story.append(_paragraph(
            table.get("title") or "Table", styles["heading"]
        ))
        if table.get("rows"):
            story.append(_report_table(table, styles))
        else:
            story.append(_paragraph(
                table.get("message") or "No rows were available.",
                styles["body"],
            ))
        story.append(Spacer(1, 6))


def _is_structured_report(payload):
    return isinstance(payload, dict) and "executive_summary" in payload


def build_pdf_report(payload, filename="report.pdf"):
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_ascii_filename(filename),
        author="InsightAI",
    )
    styles = _styles()
    story = []

    if _is_structured_report(payload):
        _report_header(story, payload, styles)
        _report_executive_section(story, payload, styles)
        story.append(PageBreak())
        _report_kpi_section(story, payload, styles)
        _report_charts_section(story, payload, styles)
        story.append(PageBreak())
        _report_detection_notes(story, payload, styles)
        _report_tables_section(story, payload, styles)
    else:
        _summary_section(story, payload, styles)
        story.append(PageBreak())
        _anomaly_section(story, payload, styles)
        _trend_section(story, payload, styles)
        _root_cause_section(story, payload, styles)
        story.append(PageBreak())
        _alerts_section(story, payload, styles)
        _recommendation_section(story, payload, styles)

    document.build(story)
    return buffer.getvalue()
