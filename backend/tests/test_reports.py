import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

import main
from reporting import (
    ReportValidationError,
    build_report_payload,
    validate_report_payload,
)


client = TestClient(main.app)


def upload_df(df, filename="reports.csv"):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return client.post(
        "/upload",
        files={"file": (filename, buffer.getvalue(), "text/csv")},
    )


def test_create_report_reuses_existing_analysis(anomaly_df, monkeypatch):
    assert upload_df(anomaly_df).status_code == 200
    insights = client.get("/insights").json()

    def fail(*args, **kwargs):
        raise AssertionError("Analytics were recalculated.")

    for name in (
        "generate_analysis",
        "detect_anomalies",
        "detect_trend_anomalies",
        "analyze_root_cause",
        "generate_kpi_alerts",
        "generate_recommendations",
    ):
        monkeypatch.setattr(main, name, fail)

    response = client.post("/reports", json={
        "title": "Quarterly Review",
        "notes": "Board pack",
    })

    assert response.status_code == 201
    body = response.json()
    report = body["report"]

    assert body["kind"] == "business_report"
    assert body["filename"] == "reports.csv"
    assert report["title"] == "Quarterly Review"
    assert report["notes"] == "Board pack"
    assert report["source_insight_id"] == insights["insight_id"]
    assert report["executive_summary"]["headline"]
    assert report["executive_summary"]["paragraphs"]
    assert len(report["charts"]) == 3
    assert report["charts"][0]["data"]
    assert report["kpi_performance"]["kpis"]
    assert report["recommendations"] == insights["recommendations"]
    assert report["anomalies"] == insights["anomalies"]
    assert report["root_cause"] == insights["root_cause"]
    assert any(
        table["id"] == "anomalies" and table["rows"]
        for table in report["tables"]
    )


def test_report_validation_handles_missing_and_invalid_values():
    with pytest.raises(ReportValidationError):
        validate_report_payload({})

    analysis = {
        "summary": {
            "columns": ["Sales"],
            "total_sales": float("nan"),
            "total_records": 3,
        }
    }
    payload = build_report_payload(analysis, {}, filename="clean.csv")

    metrics = payload["executive_summary"]["metrics"]
    assert all(metric["key"] != "total_sales" for metric in metrics)
    assert payload["charts"][0]["data"] == []
    assert "NaN" not in str(payload)

    payload["charts"][0]["data"] = [{"label": "A", "value": float("nan")}]
    with pytest.raises(ReportValidationError):
        validate_report_payload(payload)

    payload = build_report_payload({}, {}, filename="clean.csv")
    payload["report_version"] = 99
    with pytest.raises(ReportValidationError):
        validate_report_payload(payload)


def test_pdf_export_for_generated_and_current_report(anomaly_df):
    assert upload_df(anomaly_df).status_code == 200
    report_id = client.post("/reports").json()["id"]

    for path in (f"/reports/{report_id}/pdf", "/reports/current/pdf"):
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content.startswith(b"%PDF")
        assert len(response.content) > 1000
        assert "attachment" in response.headers["content-disposition"]
        assert ".pdf" in response.headers["content-disposition"]

    assert client.get("/report").content.startswith(b"%PDF")


def test_excel_export_includes_tables_and_charts(anomaly_df):
    assert upload_df(anomaly_df).status_code == 200
    report_id = client.post("/reports").json()["id"]

    response = client.get(f"/reports/{report_id}/excel")
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert response.content.startswith(b"PK")

    workbook = load_workbook(io.BytesIO(response.content))

    assert "Executive Summary" in workbook.sheetnames
    assert "KPI Performance" in workbook.sheetnames
    assert "Sales by Product" in workbook.sheetnames
    assert "Business Recommendations" in workbook.sheetnames
    assert workbook["Sales by Product"]._charts

    summary_values = [
        cell.value
        for row in workbook["Executive Summary"].iter_rows()
        for cell in row
    ]
    assert len(anomaly_df) in summary_values

    assert client.get("/reports/current/excel").status_code == 200


def test_report_handles_empty_datasets_and_missing_values():
    df = pd.DataFrame({"Misc": ["a", "b", "c", "d"]})
    assert upload_df(df).status_code == 200

    response = client.post("/reports")
    assert response.status_code == 201

    body = response.json()
    report = body["report"]
    metric_keys = {
        metric["key"] for metric in report["executive_summary"]["metrics"]
    }

    assert "total_sales" not in metric_keys
    assert "total_profit" not in metric_keys
    assert all(not chart["data"] for chart in report["charts"])
    assert report["warnings"]
    assert "NaN" not in response.text
    assert "Infinity" not in response.text
    assert client.get(f"/reports/{body['id']}/pdf").status_code == 200
    assert client.get(f"/reports/{body['id']}/excel").status_code == 200


def test_report_history_lifecycle(anomaly_df):
    assert upload_df(anomaly_df).status_code == 200
    first = client.post("/reports", json={"title": "First"}).json()["id"]
    second = client.post("/reports", json={"title": "Second"}).json()["id"]

    listing = client.get("/reports").json()
    assert listing["total"] == 2
    assert all(item["kind"] == "business_report" for item in listing["items"])
    assert listing["items"][0]["id"] == second

    detail = client.get(f"/reports/{first}").json()
    assert detail["payload"]["title"] == "First"
    assert detail["dataset_hash"]

    deleted = client.delete(f"/reports/{first}")
    assert deleted.json() == {"deleted": True, "id": first}
    assert client.get(f"/reports/{first}").status_code == 404
    assert client.get(f"/reports/{first}/pdf").status_code == 404
    assert client.delete(f"/reports/{first}").status_code == 404
    assert client.get("/history").json()["total"] >= 3


def test_report_endpoints_require_upload_and_reject_bad_ids():
    assert client.post("/reports").status_code == 400
    assert client.get("/reports/current/pdf").status_code == 400
    assert client.get("/reports/current/excel").status_code == 400
    assert client.get("/reports").json()["total"] == 0

    assert client.get("/reports/999999").status_code == 404
    assert client.get("/reports/999999/pdf").status_code == 404
    assert client.delete("/reports/999999").status_code == 404


def test_report_validation_error_is_not_exposed(monkeypatch, normal_df):
    assert upload_df(normal_df).status_code == 200

    def fail(*args, **kwargs):
        raise ReportValidationError("SECRET_VALIDATION_DETAIL")

    monkeypatch.setattr(main, "build_report_payload", fail)

    response = client.post("/reports")
    assert response.status_code == 400
    assert "SECRET_VALIDATION_DETAIL" not in response.text
