import pandas as pd

from analytics import generate_analysis
from anomaly_detection import detect_anomalies, detect_trend_anomalies
from kpi_alerts import generate_kpi_alerts
from recommendations import generate_recommendations
from root_cause import analyze_root_cause


def run_pipeline(df):
    analysis = generate_analysis(df)
    anomalies = detect_anomalies(df)
    trends = detect_trend_anomalies(df)
    root_cause = analyze_root_cause(df, trends)
    alerts = generate_kpi_alerts(df)
    recs = generate_recommendations(
        analysis, anomalies, trends, root_cause, alerts
    )
    return analysis, anomalies, trends, root_cause, alerts, recs


def test_recommendation_structure(anomaly_df):
    _, _, _, _, _, recs = run_pipeline(anomaly_df)

    assert len(recs) >= 1
    for rec in recs:
        assert rec["id"]
        assert rec["title"]
        assert rec["recommendation"]
        assert rec["reason"]
        assert rec["priority"] in ("high", "medium", "low")
        assert isinstance(rec["evidence"], list)
        for evidence in rec["evidence"]:
            assert evidence["label"]
            assert evidence["format"] in (
                "currency", "percent", "number", "text"
            )


def test_anomaly_recommendation_uses_verified_numbers(anomaly_df):
    _, anomalies, _, _, _, recs = run_pipeline(anomaly_df)

    rec = next(
        item for item in recs if item["id"] == "investigate_anomalies"
    )
    assert rec["priority"] == "high"

    count_evidence = next(
        item for item in rec["evidence"]
        if item["label"] == "Unusual records"
    )
    assert count_evidence["value"] == anomalies["anomaly_count"]


def test_decline_recommendation_matches_root_cause():
    df = pd.DataFrame({
        "Date": pd.to_datetime([
            "2024-01-15", "2024-01-15", "2024-02-15", "2024-02-15",
        ]),
        "Product": ["Mobile", "Laptop", "Mobile", "Laptop"],
        "Sales": [1000.0, 2000.0, 400.0, 1600.0],
        "Profit": [150.0, 300.0, 60.0, 240.0],
        "Quantity": [1, 2, 1, 2],
    })
    _, _, _, root_cause, _, recs = run_pipeline(df)

    rec = next(
        item for item in recs if item["id"] == "address_sales_decline"
    )
    change_evidence = next(
        item for item in rec["evidence"]
        if item["label"] == "Sales change"
    )
    assert change_evidence["value"] == root_cause["total_change"] == -1000.0


def test_clean_dataset_gets_monitor_recommendation(normal_df):
    _, _, _, _, _, recs = run_pipeline(normal_df)

    ids = [item["id"] for item in recs]
    assert "investigate_anomalies" not in ids
    assert "address_sales_decline" not in ids
    assert "monitor" in ids


def test_negative_profit_recommendation():
    df = pd.DataFrame({
        "Product": ["A", "B"] * 10,
        "Sales": [1000.0, 2000.0] * 10,
        "Profit": [-500.0, -800.0] * 10,
    })
    _, _, _, _, _, recs = run_pipeline(df)

    rec = next(
        item for item in recs if item["id"] == "fix_negative_profit"
    )
    assert rec["priority"] == "high"
    profit_evidence = next(
        item for item in rec["evidence"]
        if item["label"] == "Total profit"
    )
    assert profit_evidence["value"] == -13000.0


def test_no_fabricated_evidence(anomaly_df):
    analysis, anomalies, trends, root_cause, alerts, recs = run_pipeline(
        anomaly_df
    )

    known_numbers = set()

    def collect(value):
        if isinstance(value, (int, float)):
            known_numbers.add(round(float(value), 2))
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(analysis)
    collect(anomalies)
    collect(trends)
    collect(root_cause)
    collect(alerts)
    known_numbers.add(
        round(analysis["summary"]["total_profit"]
              / analysis["summary"]["total_sales"] * 100, 2)
    )
    for product in analysis.get("product_data", []):
        if analysis["summary"]["total_sales"]:
            known_numbers.add(round(
                product["sales"]
                / analysis["summary"]["total_sales"] * 100, 2
            ))

    for rec in recs:
        for evidence in rec["evidence"]:
            value = evidence["value"]
            if isinstance(value, (int, float)):
                assert round(float(value), 2) in known_numbers, (
                    rec["id"], evidence
                )
