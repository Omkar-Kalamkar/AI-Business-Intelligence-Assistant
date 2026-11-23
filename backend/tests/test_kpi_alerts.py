import pandas as pd
import pytest

from kpi_alerts import generate_kpi_alerts


def make_two_period_df(previous_sales, current_sales):
    return pd.DataFrame({
        "Date": pd.to_datetime([
            "2024-01-15", "2024-01-15",
            "2024-02-15", "2024-02-15",
        ]),
        "Product": ["Mobile", "Laptop", "Mobile", "Laptop"],
        "Sales": [
            previous_sales * 0.4, previous_sales * 0.6,
            current_sales * 0.4, current_sales * 0.6,
        ],
        "Profit": [
            previous_sales * 0.06, previous_sales * 0.09,
            current_sales * 0.06, current_sales * 0.09,
        ],
        "Quantity": [1, 1, 1, 1],
    })


def test_critical_decrease_alert():
    df = make_two_period_df(3000, 2000)
    result = generate_kpi_alerts(df)

    assert result["available"] is True
    assert result["mode"] == "period_comparison"

    alert = next(
        item for item in result["alerts"] if item["kpi"] == "total_sales"
    )
    assert alert["severity"] == "critical"
    assert alert["direction"] == "decrease"
    assert alert["change_pct"] == -33.33
    assert alert["current"] == 2000.0
    assert alert["previous"] == 3000.0
    assert alert["change"] == -1000.0


def test_warning_increase_alert():
    df = make_two_period_df(3000, 3600)
    result = generate_kpi_alerts(df)

    alert = next(
        item for item in result["alerts"] if item["kpi"] == "total_sales"
    )
    assert alert["severity"] == "warning"
    assert alert["direction"] == "increase"
    assert alert["change_pct"] == 20.0


def test_small_change_produces_no_alert():
    df = make_two_period_df(3000, 3050)
    result = generate_kpi_alerts(df)

    assert result["available"] is True
    assert result["alerts"] == []


def test_stable_periods_produce_no_alerts():
    df = make_two_period_df(3000, 3000)
    result = generate_kpi_alerts(df)
    assert result["alerts"] == []


def test_baseline_mode_without_dates():
    df = pd.DataFrame({
        "Product": ["A", "B", "C"],
        "Sales": [1000.0, 2000.0, 3000.0],
        "Profit": [-100.0, -200.0, -300.0],
    })
    result = generate_kpi_alerts(df)

    assert result["available"] is True
    assert result["mode"] == "baseline"

    alert = next(
        item for item in result["alerts"]
        if item["id"] == "negative_profit"
    )
    assert alert["severity"] == "critical"
    assert alert["current"] == -600.0


def test_baseline_low_margin_warning():
    df = pd.DataFrame({
        "Sales": [1000.0] * 10,
        "Profit": [20.0] * 10,
    })
    result = generate_kpi_alerts(df)

    assert result["mode"] == "baseline"
    assert any(
        item["id"] == "low_margin" for item in result["alerts"]
    )


def test_requires_numeric_business_column():
    df = pd.DataFrame({"Product": ["A", "B"]})
    result = generate_kpi_alerts(df)
    assert result["available"] is False


def test_partial_trailing_period_is_not_compared():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({
        "Date": dates,
        "Sales": [100.0] * 30,
        "Profit": [15.0] * 30,
        "Quantity": [1] * 30,
    })
    result = generate_kpi_alerts(df)

    assert result["alerts"] == []
