
import pandas as pd


def generate_analysis(df):

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    # Find columns without depending on capitalization
    column_lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    sales_col = column_lookup.get("sales") or column_lookup.get("revenue")
    profit_col = column_lookup.get("profit")
    quantity_col = column_lookup.get("quantity")
    product_col = column_lookup.get("product")
    region_col = column_lookup.get("region")

    summary = {
        "total_records": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_records": int(df.duplicated().sum()),
        "total_sales": float(df[sales_col].sum()) if sales_col else 0,
        "total_profit": float(df[profit_col].sum()) if profit_col else 0,
        "total_quantity": int(df[quantity_col].sum()) if quantity_col else 0
    }

    statistics = {}

    for column in numeric_columns:
        statistics[column] = {
            "total": round(float(df[column].sum()), 2),
            "average": round(float(df[column].mean()), 2),
            "maximum": round(float(df[column].max()), 2),
            "minimum": round(float(df[column].min()), 2)
        }

    product_data = []

    if sales_col and product_col:
        grouped = (
            df.groupby(product_col)[sales_col]
            .sum()
            .reset_index()
        )

        product_data = [
            {"name": str(row[product_col]),
             "sales": float(row[sales_col])}
            for _, row in grouped.iterrows()
        ]

    region_data = []

    if sales_col and region_col:
        grouped = (
            df.groupby(region_col)[sales_col]
            .sum()
            .reset_index()
        )

        region_data = [
            {"name": str(row[region_col]),
             "value": float(row[sales_col])}
            for _, row in grouped.iterrows()
        ]

    insights = []

    if sales_col:
        insights.append(
            f"Total sales are {df[sales_col].sum():,.2f}."
        )

    if profit_col:
        insights.append(
            f"Total profit is {df[profit_col].sum():,.2f}."
        )

    if product_data:
        best_product = max(product_data, key=lambda x: x["sales"])
        insights.append(
            f"Top performing product: {best_product['name']}."
        )

    if region_data:
        best_region = max(region_data, key=lambda x: x["value"])
        insights.append(
            f"Top performing region: {best_region['name']}."
        )

    return {
        "summary": summary,
        "statistics": statistics,
        "product_data": product_data,
        "region_data": region_data,
        "insights": insights
    }
