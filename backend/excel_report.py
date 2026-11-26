import io
import json
import math
import re

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from reporting import validate_report_payload


HEADER_FILL = PatternFill("solid", fgColor="EEF2FF")
HEADER_FONT = Font(bold=True, color="312E81")
TITLE_FONT = Font(bold=True, size=16, color="312E81")


def _cell_value(value):
    if value is None:
        return None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=str)
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _number_format(value_format):
    if value_format in ("currency", "number", "percent"):
        return "#,##0.00"
    return None


def _apply_format(cell, value_format):
    number_format = _number_format(value_format)
    if number_format:
        cell.number_format = number_format


def _sheet_name(name, used, fallback):
    cleaned = re.sub(r"[\\/*?:\[\]]", "_", str(name or fallback))
    cleaned = cleaned.strip(" _'")[:31] or fallback[:31]

    if cleaned not in used:
        used.add(cleaned)
        return cleaned

    index = 2
    while True:
        suffix = f"_{index}"
        candidate = cleaned[:31 - len(suffix)] + suffix
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _style_header(sheet, row, count):
    for column in range(1, count + 1):
        cell = sheet.cell(row=row, column=column)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="top")


def _write_summary(sheet, report):
    summary = report["executive_summary"]
    performance = report["kpi_performance"]
    sheet["A1"] = report["title"]
    sheet["A1"].font = TITLE_FONT

    row = 3
    details = (
        ("Dataset", report.get("filename")),
        ("Generated", report.get("generated_at")),
        ("Notes", report.get("notes") or "—"),
        ("Headline", summary.get("headline")),
    )
    for label, value in details:
        sheet.cell(row=row, column=1, value=label).font = Font(bold=True)
        sheet.cell(row=row, column=2, value=_cell_value(value))
        row += 1

    row += 1
    sheet.cell(row=row, column=1, value="Executive narrative").font = (
        Font(bold=True, color="312E81")
    )
    row += 1
    for paragraph in summary["paragraphs"]:
        cell = sheet.cell(row=row, column=2, value=_cell_value(paragraph))
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1

    row += 1
    sheet.cell(row=row, column=1, value="Highlights").font = (
        Font(bold=True, color="312E81")
    )
    row += 1
    for highlight in summary["highlights"]:
        cell = sheet.cell(row=row, column=2, value=_cell_value(highlight))
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1

    row += 1
    header_row = row
    sheet.cell(row=row, column=1, value="Metric")
    sheet.cell(row=row, column=2, value="Value")
    _style_header(sheet, row, 2)
    row += 1
    for metric in summary["metrics"]:
        sheet.cell(row=row, column=1, value=metric.get("label"))
        value_cell = sheet.cell(
            row=row, column=2, value=_cell_value(metric.get("value"))
        )
        _apply_format(value_cell, metric.get("format"))
        row += 1

    row += 1
    sheet.cell(row=row, column=1, value="KPI context").font = (
        Font(bold=True, color="312E81")
    )
    row += 1
    for label, value in (
        ("Mode", performance.get("mode") or "—"),
        ("Current period", performance.get("current_period") or "—"),
        ("Previous period", performance.get("previous_period") or "—"),
        ("Message", performance.get("message")),
    ):
        sheet.cell(row=row, column=1, value=label).font = Font(bold=True)
        sheet.cell(row=row, column=2, value=_cell_value(value))
        row += 1

    warnings = report.get("warnings") or []
    if warnings:
        row += 1
        sheet.cell(row=row, column=1, value="Warnings").font = (
            Font(bold=True, color="B45309")
        )
        row += 1
        for warning in warnings:
            sheet.cell(row=row, column=2, value=_cell_value(warning))
            row += 1

    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 95
    sheet.freeze_panes = f"A{header_row + 1}"


def _write_table(workbook, table, used):
    columns = table["columns"]
    sheet = workbook.create_sheet(
        _sheet_name(table["title"], used, table["id"])
    )

    sheet.append([column["label"] for column in columns])
    _style_header(sheet, 1, len(columns))

    rows = table["rows"]
    if rows:
        for row in rows:
            values = []
            formats = []
            for column in columns:
                key = column["key"]
                value = row.get(key) if isinstance(row, dict) else None
                if key == "current" and row.get("format") in (
                    "currency", "number", "percent"
                ):
                    formats.append(row["format"])
                else:
                    formats.append(column.get("format"))
                values.append(_cell_value(value))
            sheet.append(values)
            for index, value_format in enumerate(formats, start=1):
                _apply_format(sheet.cell(row=sheet.max_row, column=index),
                              value_format)
    else:
        sheet.append([table.get("message") or "No rows available"])
        sheet.cell(row=2, column=1).font = Font(italic=True, color="64748B")

    sheet.freeze_panes = "A2"
    if rows:
        sheet.auto_filter.ref = (
            f"A1:{get_column_letter(len(columns))}{sheet.max_row}"
        )
    for index, column in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(
            16, min(48, len(column["label"]) + 6)
        )
    return sheet


def _write_chart(workbook, chart, used):
    sheet = workbook.create_sheet(
        _sheet_name(chart["title"], used, chart["id"])
    )
    data = chart["data"]

    sheet.append(["Label", "Value"])
    _style_header(sheet, 1, 2)

    if data:
        for point in data:
            sheet.append([
                _cell_value(point.get("label")),
                _cell_value(point.get("value")),
            ])
    else:
        sheet.append([chart.get("message") or "No data available"])
        sheet.cell(row=2, column=1).font = Font(italic=True, color="64748B")

    if data:
        chart_type = chart["type"]
        if chart_type == "pie":
            graphic = PieChart()
        elif chart_type == "line":
            graphic = LineChart()
        else:
            graphic = BarChart()

        graphic.title = chart["title"]
        graphic.height = 9
        graphic.width = 18
        if chart_type != "pie":
            graphic.y_axis.title = "Value"
        graphic.add_data(
            Reference(sheet, min_col=2, min_row=1, max_row=len(data) + 1),
            titles_from_data=True,
        )
        graphic.set_categories(
            Reference(sheet, min_col=1, min_row=2, max_row=len(data) + 1)
        )
        sheet.add_chart(graphic, "D2")

    sheet.column_dimensions["A"].width = 26
    sheet.column_dimensions["B"].width = 16
    sheet.freeze_panes = "A2"


def build_excel_report(payload, filename=None):
    validate_report_payload(payload)

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Executive Summary"
    _write_summary(summary_sheet, payload)
    if filename:
        workbook.properties.title = str(filename)

    used_names = {"Executive Summary"}
    for table in payload["tables"]:
        _write_table(workbook, table, used_names)

    for chart in payload["charts"]:
        _write_chart(workbook, chart, used_names)

    alerts = payload["kpi_performance"]["alerts"]
    if alerts:
        alert_rows = []
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            alert_rows.append({
                "severity": alert.get("severity"),
                "label": alert.get("label"),
                "message": alert.get("message"),
                "current": alert.get("current"),
                "previous": alert.get("previous"),
                "change_pct": alert.get("change_pct"),
            })
        _write_table(workbook, {
            "id": "kpi_alerts",
            "title": "KPI Alerts",
            "columns": [
                {"key": "severity", "label": "Severity", "format": "text"},
                {"key": "label", "label": "KPI", "format": "text"},
                {"key": "message", "label": "Message", "format": "text"},
                {"key": "current", "label": "Current", "format": "number"},
                {"key": "previous", "label": "Previous", "format": "number"},
                {
                    "key": "change_pct",
                    "label": "Change %",
                    "format": "percent",
                },
            ],
            "rows": alert_rows,
            "message": "",
        }, used_names)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
