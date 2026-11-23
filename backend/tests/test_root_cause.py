import pandas as pd
import pytest

from root_cause import analyze_root_cause


@pytest.fixture
def decline_df():
    return pd.DataFrame({
        "Date": pd.to_datetime([
            "2024-01-15", "2024-01-15", "2024-01-15",
            "2024-02-15", "2024-02-15",
        ]),
        "Product": ["Mobile", "Mobile", "Laptop", "Mobile", "Laptop"],
        "Region": ["North", "South", "North", "North", "South"],
        "Sales": [600.0, 400.0, 2000.0, 400.0, 1600.0],
        "Profit": [90.0, 60.0, 300.0, 60.0, 240.0],
        "Quantity": [1, 1, 2, 1, 2],
    })


def test_period_comparison_numbers(decline_df):
    result = analyze_root_cause(decline_df)

    assert result["available"] is True
    assert result["mode"] == "period_comparison"
    assert result["current_period"] == "2024-02-15"
    assert result["previous_period"] == "2024-01-15"
    assert result["current_total"] == 2000.0
    assert result["previous_total"] == 3000.0
    assert result["total_change"] == -1000.0
    assert result["total_change_pct"] == -33.33

    products = next(
        breakdown for breakdown in result["dimensions"]
        if breakdown["dimension"] == "product"
    )
    mobile = next(
        item for item in products["contributors"]
        if item["name"] == "Mobile"
    )
    laptop = next(
        item for item in products["contributors"]
        if item["name"] == "Laptop"
    )

    assert mobile["current"] == 400.0
    assert mobile["previous"] == 1000.0
    assert mobile["change"] == -600.0
    assert mobile["contribution_pct"] == 60.0
    assert laptop["change"] == -400.0
    assert laptop["contribution_pct"] == 40.0

    assert result["top_mover"]["name"] == "Mobile"
    assert result["top_mover"]["change"] == -600.0
    assert "contributed" in result["summary"] or "contributions" in result["summary"]


def test_contribution_mode_without_dates(decline_df):
    result = analyze_root_cause(decline_df.drop(columns=["Date"]))

    assert result["available"] is True
    assert result["mode"] == "contribution"
    assert result["total_change"] is None

    products = next(
        breakdown for breakdown in result["dimensions"]
        if breakdown["dimension"] == "product"
    )
    shares = [
        item["contribution_pct"] for item in products["contributors"]
    ]
    assert sum(shares) == pytest.approx(100.0, abs=0.1)


def test_requires_sales_column():
    df = pd.DataFrame({"Product": ["A", "B"], "Quantity": [1, 2]})
    result = analyze_root_cause(df)
    assert result["available"] is False


def test_no_dimensions_and_no_dates_is_unavailable():
    df = pd.DataFrame({"Sales": [100.0, 200.0, 300.0]})
    result = analyze_root_cause(df)
    assert result["available"] is False
