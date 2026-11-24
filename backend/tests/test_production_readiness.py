import io
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import data_processing
import main


client = TestClient(main.app)
DATASETS_DIR = Path(__file__).resolve().parents[2] / "datasets"


def upload_csv(df, filename="test.csv"):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return client.post(
        "/upload",
        files={"file": (filename, buffer.getvalue(), "text/csv")},
    )


def test_upload_rejects_oversized_file(monkeypatch, normal_df):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 32)

    response = upload_csv(normal_df)

    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


def test_upload_enforces_row_limit(monkeypatch, normal_df):
    monkeypatch.setattr(data_processing, "MAX_DATASET_ROWS", 5)

    response = upload_csv(normal_df)

    assert response.status_code == 400
    assert "too many rows" in response.json()["detail"]


def test_upload_rejects_binary_csv():
    response = client.post(
        "/upload",
        files={"file": ("broken.csv", b"PK\x03\x04binary", "text/csv")},
    )

    assert response.status_code == 400


def test_upload_rejects_fake_excel_file():
    response = client.post(
        "/upload",
        files={"file": ("broken.xlsx", b"not an excel file",
                        "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet")},
    )

    assert response.status_code == 400


def test_upload_handles_rows_that_become_empty():
    response = client.post(
        "/upload",
        files={"file": ("empty_rows.csv", "Sales,Product\n,\n,\n",
                        "text/csv")},
    )

    assert response.status_code == 400
    assert "no usable records" in response.json()["detail"]


def test_upload_sanitizes_filename(normal_df):
    response = upload_csv(normal_df, filename="../../evil?.csv")

    assert response.status_code == 200
    filename = response.json()["filename"]
    assert "/" not in filename
    assert ".." not in filename
    assert filename.endswith(".csv")


def test_upload_does_not_expose_internal_errors(monkeypatch, normal_df):
    def fail(*args, **kwargs):
        raise RuntimeError("SECRET_INTERNAL_DETAIL")

    monkeypatch.setattr(main, "generate_analysis", fail)

    response = upload_csv(normal_df)

    assert response.status_code == 500
    assert "SECRET_INTERNAL_DETAIL" not in response.json()["detail"]


def test_ask_validates_empty_question():
    response = client.post("/ask", json={"question": ""})

    assert response.status_code == 422


def test_report_download_for_current_insights(anomaly_df):
    assert upload_csv(anomaly_df, "report_data.csv").status_code == 200
    insights = client.get("/insights").json()

    response = client.get("/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert str(insights["insight_id"]) in response.headers["content-disposition"]


def test_report_download_for_saved_insight(anomaly_df):
    assert upload_csv(anomaly_df).status_code == 200
    insights = client.get("/insights").json()

    response = client.get(f"/report/{insights['insight_id']}")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_report_download_for_upload_history(anomaly_df):
    assert upload_csv(anomaly_df).status_code == 200
    listing = client.get("/history").json()
    upload_entry = next(
        item for item in listing["items"]
        if item["kind"] == "upload_analysis"
    )

    response = client.get(f"/report/{upload_entry['id']}")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_report_requires_upload():
    assert client.get("/report").status_code == 400


def test_report_returns_404_for_unknown_insight():
    assert client.get("/report/999999").status_code == 404


def test_cors_origins_are_configurable_without_wildcard(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://app.example.com, https://admin.example.com, *",
    )

    assert main._cors_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_large_numeric_dataset_does_not_expose_nan(anomaly_df):
    assert upload_csv(anomaly_df).status_code == 200

    response = client.get("/insights")
    payload = response.content.decode("utf-8")

    assert response.status_code == 200
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_missing_columns_still_generate_insights():
    df = pd.DataFrame({"Misc": ["a", "b", "c", "d"]})

    assert upload_csv(df).status_code == 200
    response = client.get("/insights")

    assert response.status_code == 200
    assert response.json()["anomalies"]["available"] is False
    assert response.json()["root_cause"]["available"] is False


@pytest.mark.parametrize("endpoint", ["/history?limit=0", "/history?offset=-1"])
def test_history_rejects_invalid_pagination(endpoint):
    assert client.get(endpoint).status_code == 422


@pytest.mark.parametrize(
    "filename,expected_anomalies",
    [
        ("sample_sales.csv", 0),
        ("sample_sales_anomalies.csv", 2),
    ],
)
def test_sample_datasets_complete_end_to_end(filename, expected_anomalies):
    path = DATASETS_DIR / filename
    assert path.exists()

    upload = client.post(
        "/upload",
        files={"file": (filename, path.read_bytes(), "text/csv")},
    )
    assert upload.status_code == 200

    insights_response = client.get("/insights")
    assert insights_response.status_code == 200
    insights = insights_response.json()

    assert insights["summary"]["total_records"] > 0
    assert insights["anomalies"]["available"] is True
    assert insights["anomalies"]["anomaly_count"] >= expected_anomalies
    assert isinstance(insights["insight_id"], int)

    history = client.get("/history").json()
    assert any(item["kind"] == "upload_analysis" for item in history["items"])
    assert any(
        item["kind"] == "business_insights" for item in history["items"]
    )

    report = client.get("/report")
    assert report.status_code == 200
    assert report.content.startswith(b"%PDF")
