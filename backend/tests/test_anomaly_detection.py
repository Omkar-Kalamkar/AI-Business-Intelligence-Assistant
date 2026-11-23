import json

import pandas as pd

from anomaly_detection import detect_anomalies, detect_trend_anomalies


def test_normal_dataset_has_no_severe_anomalies(normal_df):
    result = detect_anomalies(normal_df)

    assert result["available"] is True
    assert result["anomaly_count"] <= 2
    assert "critical" not in result["severity_counts"]
    assert "high" not in result["severity_counts"]


def test_spikes_are_detected_with_severity(anomaly_df):
    result = detect_anomalies(anomaly_df)

    assert result["available"] is True
    assert result["anomaly_count"] >= 2

    flagged_rows = {item["row_index"] for item in result["anomalies"]}
    assert 50 in flagged_rows
    assert 120 in flagged_rows

    severe = [
        item for item in result["anomalies"]
        if item["severity"] in ("critical", "high")
    ]
    assert len(severe) >= 2

    spike = next(
        item for item in result["anomalies"] if item["row_index"] == 50
    )
    sales_flag = next(
        flag for flag in spike["flagged_columns"]
        if flag["column"] == "Sales"
    )
    assert sales_flag["value"] == 90000.0
    assert 800 <= sales_flag["expected_median"] <= 1200
    assert sales_flag["lower_bound"] < sales_flag["upper_bound"]
    assert sales_flag["zscore"] > 3.5
    assert "statistical" in spike["detected_by"]


def test_missing_and_invalid_values_do_not_crash(missing_df):
    result = detect_anomalies(missing_df)

    assert result["available"] is True
    json.dumps(result, allow_nan=False)


def test_non_numeric_dataset_is_unavailable():
    df = pd.DataFrame({
        "Product": ["A", "B"] * 20,
        "Region": ["N", "S"] * 20,
    })
    result = detect_anomalies(df)

    assert result["available"] is False
    assert result["anomalies"] == []


def test_small_dataset_is_unavailable(normal_df):
    result = detect_anomalies(normal_df.head(3))
    assert result["available"] is False


def test_constant_column_is_unavailable():
    df = pd.DataFrame({"Sales": [100.0] * 30})
    result = detect_anomalies(df)
    assert result["available"] is False


def test_trend_anomalies_on_normal_data(normal_df):
    result = detect_trend_anomalies(normal_df)

    assert result["available"] is True
    assert result["anomaly_count"] <= 1
    assert result["period_count"] >= 6


def test_trend_anomalies_flag_spikes(anomaly_df):
    result = detect_trend_anomalies(anomaly_df)

    assert result["available"] is True
    assert result["anomaly_count"] >= 2

    flagged = [
        period for period in result["periods"] if period["is_anomaly"]
    ]
    assert all(period["severity"] for period in flagged)
    assert all(period["deviation_pct"] is not None for period in flagged)


def test_trend_requires_date_column(normal_df):
    result = detect_trend_anomalies(normal_df.drop(columns=["Date"]))
    assert result["available"] is False


def test_trend_requires_enough_periods():
    df = pd.DataFrame({
        "Date": pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03"] * 4
        ),
        "Sales": [100.0] * 12,
    })
    result = detect_trend_anomalies(df)
    assert result["available"] is False


def test_monthly_trend_detects_spike_and_drop(monthly_df):
    result = detect_trend_anomalies(monthly_df)

    assert result["available"] is True
    flagged_periods = [
        period["period"]
        for period in result["periods"] if period["is_anomaly"]
    ]

    assert any(period.startswith("2024-06") for period in flagged_periods)
    assert any(period.startswith("2024-10") for period in flagged_periods)

    spike = next(
        period for period in result["periods"]
        if period["period"].startswith("2024-06") and period["is_anomaly"]
    )
    assert spike["direction"] == "above"
    assert spike["deviation_pct"] > 0
