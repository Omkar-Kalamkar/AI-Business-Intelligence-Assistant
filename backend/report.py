import io
import json
import re

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
