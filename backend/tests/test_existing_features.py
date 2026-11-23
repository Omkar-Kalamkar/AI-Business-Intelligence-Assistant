import pandas as pd
import pytest

from ai_assistant import answer_question
from analytics import compare_sales, generate_analysis


def test_generate_analysis_shape_and_totals(normal_df):
    analysis = generate_analysis(normal_df)

    assert set(analysis.keys()) == {
        "summary", "statistics", "product_data",
        "region_data", "insights", "recommendations",
    }

    summary = analysis["summary"]
    assert summary["total_records"] == len(normal_df)
    assert summary["total_sales"] == pytest.approx(
        normal_df["Sales"].sum(), abs=0.01
    )
    assert summary["total_profit"] == pytest.approx(
        normal_df["Profit"].sum(), abs=0.01
    )

    assert len(analysis["product_data"]) == 3
    assert len(analysis["region_data"]) == 4
    assert all(
        isinstance(item, str) for item in analysis["recommendations"]
    )


def test_compare_sales_math(normal_df):
    result = compare_sales(normal_df, "product", "Mobile", "Laptop")

    mobile = normal_df.loc[
        normal_df["Product"] == "Mobile", "Sales"
    ].sum()
    laptop = normal_df.loc[
        normal_df["Product"] == "Laptop", "Sales"
    ].sum()

    assert result["difference"] == pytest.approx(abs(mobile - laptop))
    expected_winner = "Mobile" if mobile > laptop else "Laptop"
    assert result["higher_performer"] == expected_winner


def test_answer_question_without_insights(normal_df):
    answer = answer_question(normal_df, "total sales")
    assert "Total sales" in answer

    answer = answer_question(normal_df, "top product")
    assert "top-selling" in answer

    answer = answer_question(normal_df, "something unrelated")
    assert "I can answer questions" in answer


def test_answer_question_insights_optional(normal_df):
    answer = answer_question(
        normal_df, "total sales", insights=None
    )
    assert "Total sales" in answer
