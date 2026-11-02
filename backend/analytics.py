
import pandas as pd


def generate_analysis(df):

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    # Basic dataset information
    summary = {
        "total_records": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_records": int(df.duplicated().sum())
    }

    # Calculate statistics for numeric columns
    statistics = {}

    for column in numeric_columns:

        statistics[column] = {
            "total": round(float(df[column].sum()), 2),
            "average": round(float(df[column].mean()), 2),
            "maximum": round(float(df[column].max()), 2),
            "minimum": round(float(df[column].min()), 2)
        }

    # Generate automatic insights
    insights = []

    if numeric_columns:
        for column in numeric_columns:

            highest = df[column].max()
            lowest = df[column].min()

            insights.append(
                f"{column}: Highest value is {highest} "
                f"and lowest value is {lowest}."
            )

    # Find most frequent value in categorical columns
    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns

    for column in categorical_columns:

        if not df[column].dropna().empty:

            top_value = df[column].mode().iloc[0]

            insights.append(
                f"Most frequent {column}: {top_value}"
            )

    return {
        "summary": summary,
        "statistics": statistics,
        "insights": insights
    }
