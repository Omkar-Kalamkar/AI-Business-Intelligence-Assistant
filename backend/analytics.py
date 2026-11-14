
import pandas as pd


def generate_analysis(df):

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    # Identify columns without depending on capitalization
    column_lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    sales_col = column_lookup.get("sales") or column_lookup.get("revenue")
    profit_col = column_lookup.get("profit")
    quantity_col = column_lookup.get("quantity")
    product_col = column_lookup.get("product")
    region_col = column_lookup.get("region")

    # Summary
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

    # Numeric statistics
    statistics = {}

    for column in numeric_columns:
        statistics[column] = {
            "total": round(float(df[column].sum()), 2),
            "average": round(float(df[column].mean()), 2),
            "maximum": round(float(df[column].max()), 2),
            "minimum": round(float(df[column].min()), 2)
        }

    # Product sales analysis
    product_data = []

    if sales_col and product_col:
        grouped = (
            df.groupby(product_col)[sales_col]
            .sum()
            .reset_index()
        )

        product_data = [
            {
                "name": str(row[product_col]),
                "sales": float(row[sales_col])
            }
            for _, row in grouped.iterrows()
        ]

    # Region sales analysis
    region_data = []

    if sales_col and region_col:
        grouped = (
            df.groupby(region_col)[sales_col]
            .sum()
            .reset_index()
        )

        region_data = [
            {
                "name": str(row[region_col]),
                "value": float(row[sales_col])
            }
            for _, row in grouped.iterrows()
        ]

    # Basic business insights
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

    # Advanced business recommendations
    recommendations = []

    if sales_col and product_data:

        sorted_products = sorted(
            product_data,
            key=lambda x: x["sales"],
            reverse=True
        )

        best_product = sorted_products[0]
        lowest_product = sorted_products[-1]

        recommendations.append(
            f"Focus on promoting {best_product['name']}, "
            f"which has the highest sales of "
            f"{best_product['sales']:,.2f}."
        )

        if len(sorted_products) > 1:
            recommendations.append(
                f"Review the sales performance of "
                f"{lowest_product['name']}, which has the lowest "
                f"sales of {lowest_product['sales']:,.2f}. "
                f"Consider targeted promotions or customer feedback."
            )

    if sales_col and region_data:

        sorted_regions = sorted(
            region_data,
            key=lambda x: x["value"],
            reverse=True
        )

        best_region = sorted_regions[0]

        recommendations.append(
            f"Your strongest market is {best_region['name']}. "
            f"Study its successful sales strategies and consider "
            f"applying them in other regions."
        )

        if len(sorted_regions) > 1:
            lowest_region = sorted_regions[-1]

            recommendations.append(
                f"Investigate the {lowest_region['name']} region, "
                f"which has the lowest sales. Consider improving "
                f"marketing and customer engagement there."
            )

    if sales_col and profit_col:
        total_sales = df[sales_col].sum()
        total_profit = df[profit_col].sum()

        if total_sales > 0:
            profit_margin = (total_profit / total_sales) * 100

            recommendations.append(
                f"Your overall profit margin is "
                f"{profit_margin:.2f}%. Monitor costs and pricing "
                f"to improve profitability."
            )

        if total_profit < 0:
            recommendations.append(
                "Your business has an overall loss. Review expenses, "
                "pricing and operational costs."
            )

    # Final analysis response
    return {
        "summary": summary,
        "statistics": statistics,
        "product_data": product_data,
        "region_data": region_data,
        "insights": insights,
        "recommendations": recommendations
    }
