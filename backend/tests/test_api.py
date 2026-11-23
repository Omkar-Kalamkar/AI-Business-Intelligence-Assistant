import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def upload_df(df, filename="test.csv"):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return client.post(
        "/upload",
        files={"file": (filename, buffer.getvalue(), "text/csv")},
    )


def test_home_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}


def test_upload_normal_dataset(normal_df):
    response = upload_df(normal_df)

    assert response.status_code == 200
    body = response.json()

    assert body["message"] == "Dataset analyzed successfully!"
    assert body["filename"] == "test.csv"
    assert body["original_records"] == len(normal_df)
    assert body["cleaned_records"] == len(normal_df)
    assert body["dataset_id"]
    assert body["uploaded_at"]
    assert len(body["preview"]) == 5

    summary = body["analysis"]["summary"]
    assert summary["total_sales"] == pytest.approx(
        normal_df["Sales"].sum(), abs=0.01
    )
    assert "recommendations" in body["analysis"]


def test_upload_excel(normal_df):
    buffer = io.BytesIO()
    normal_df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = client.post(
        "/upload",
        files={"file": (
            "test.xlsx",
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet",
        )},
    )
    assert response.status_code == 200


def test_upload_invalid_extension():
    response = client.post(
        "/upload",
        files={"file": ("data.txt", "hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_empty_dataset():
    response = client.post(
        "/upload",
        files={"file": ("empty.csv", "Sales,Product\n", "text/csv")},
    )
    assert response.status_code == 400


def test_insights_requires_upload():
    assert client.get("/insights").status_code == 400


def test_insights_pipeline(anomaly_df):
    assert upload_df(anomaly_df).status_code == 200

    response = client.get("/insights")
    assert response.status_code == 200
    body = response.json()

    assert body["filename"] == "test.csv"
    assert body["dataset_id"]
    assert body["generated_at"]
    assert isinstance(body["insight_id"], int)

    assert body["anomalies"]["available"] is True
    assert body["anomalies"]["anomaly_count"] >= 2
    assert body["trends"]["available"] is True
    assert body["root_cause"]["available"] is True
    assert body["kpi_alerts"]["available"] is True
    assert len(body["recommendations"]) >= 1


def test_insights_without_saving(anomaly_df):
    upload_df(anomaly_df)
    body = client.get("/insights?save=false").json()
    assert body["insight_id"] is None


def test_insights_with_missing_values(missing_df):
    assert upload_df(missing_df).status_code == 200
    response = client.get("/insights")
    assert response.status_code == 200


def test_history_flow(anomaly_df):
    upload_df(anomaly_df)
    insights = client.get("/insights").json()

    listing = client.get("/history").json()
    assert listing["total"] >= 2
    kinds = {item["kind"] for item in listing["items"]}
    assert "upload_analysis" in kinds
    assert "business_insights" in kinds

    detail = client.get(f"/history/{insights['insight_id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["payload"]["filename"] == "test.csv"
    assert detail_body["dataset_hash"]
    assert detail_body["record_count"] == len(anomaly_df)

    deleted = client.delete(f"/history/{insights['insight_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    assert client.get(
        f"/history/{insights['insight_id']}"
    ).status_code == 404
    assert client.delete(
        f"/history/{insights['insight_id']}"
    ).status_code == 404


def test_ask_existing_behavior(normal_df):
    upload_df(normal_df)
    response = client.post("/ask", json={"question": "total sales"})

    assert response.status_code == 200
    assert "Total sales" in response.json()["answer"]


def test_ask_anomaly_question_after_insights(anomaly_df):
    upload_df(anomaly_df)
    client.get("/insights")

    response = client.post(
        "/ask", json={"question": "Are there any anomalies?"}
    )
    assert response.status_code == 200
    assert "unusual" in response.json()["answer"]


def test_ask_requires_upload():
    response = client.post("/ask", json={"question": "total sales"})
    assert response.status_code == 400


def test_compare_existing_behavior(normal_df):
    upload_df(normal_df)
    response = client.post("/compare", json={
        "dimension": "product",
        "item1": "Mobile",
        "item2": "Laptop",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["difference"] >= 0
    assert body["higher_performer"]
    assert len(body["comparison"]) == 2


def test_compare_invalid_dimension(normal_df):
    upload_df(normal_df)
    response = client.post("/compare", json={
        "dimension": "country",
        "item1": "A",
        "item2": "B",
    })
    assert response.status_code == 400
