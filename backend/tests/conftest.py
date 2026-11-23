import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "INSIGHTS_DB_PATH", str(tmp_path / "test_insights.db")
    )
    yield


@pytest.fixture(autouse=True)
def reset_app_state():
    import main

    main.current_df = None
    main.current_meta = None
    main.current_analysis = None
    main.current_insights = None
    yield


def make_normal_df(rows=240, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")

    return pd.DataFrame({
        "Date": dates,
        "Product": rng.choice(["Mobile", "Laptop", "Tablet"], rows),
        "Region": rng.choice(["North", "South", "East", "West"], rows),
        "Sales": rng.uniform(800, 1200, rows).round(2),
        "Profit": rng.uniform(80, 200, rows).round(2),
        "Quantity": rng.integers(1, 6, rows),
    })


@pytest.fixture
def normal_df():
    return make_normal_df()


@pytest.fixture
def anomaly_df():
    df = make_normal_df()
    df.loc[50, "Sales"] = 90000.0
    df.loc[120, "Sales"] = -5000.0
    df.loc[120, "Quantity"] = 9999
    return df


@pytest.fixture
def missing_df():
    df = make_normal_df(rows=120)
    df["Sales"] = df["Sales"].astype(object)
    df.loc[5, "Sales"] = np.nan
    df.loc[10, "Profit"] = np.nan
    df.loc[15, "Quantity"] = np.nan
    df.loc[20, "Sales"] = "not-a-number"
    df.loc[21, "Sales"] = "abc"
    return df


@pytest.fixture
def monthly_df():
    rows = []
    months = pd.date_range("2022-01-01", periods=36, freq="MS")

    for month in months:
        total = 10000
        if month == pd.Timestamp("2024-06-01"):
            total = 60000
        elif month == pd.Timestamp("2024-10-01"):
            total = 1000

        for day in (1, 8, 15, 22):
            rows.append({
                "Date": month + pd.Timedelta(days=day - 1),
                "Product": "Mobile" if day <= 15 else "Laptop",
                "Region": "North" if day <= 15 else "South",
                "Sales": total / 4,
                "Profit": total / 4 * 0.15,
                "Quantity": 2,
            })

    return pd.DataFrame(rows)
