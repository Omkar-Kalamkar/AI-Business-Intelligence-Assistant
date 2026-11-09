
def answer_question(df, question):

    question = question.lower().strip()

    # Identify available columns
    columns = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    sales_col = columns.get("sales") or columns.get("revenue")
    profit_col = columns.get("profit")
    quantity_col = columns.get("quantity")
    product_col = columns.get("product")
    region_col = columns.get("region")

    # Total sales
    if any(word in question for word in ["total sales", "total revenue"]):

        if sales_col:
            total = df[sales_col].sum()
            return f"Total sales are ₹{total:,.2f}."

        return "I couldn't find a Sales or Revenue column."

    # Total profit
    elif "profit" in question:

        if profit_col:
            total = df[profit_col].sum()
            return f"Total profit is ₹{total:,.2f}."

        return "I couldn't find a Profit column."

    # Average sales
    elif any(word in question for word in ["average sales", "average revenue"]):

        if sales_col:
            average = df[sales_col].mean()
            return f"Average sales per record are ₹{average:,.2f}."

        return "I couldn't find a Sales or Revenue column."

    # Highest selling product
    elif any(word in question for word in ["top product", "best product", "highest sales product"]):

        if sales_col and product_col:
            grouped = df.groupby(product_col)[sales_col].sum()
            product = grouped.idxmax()
            amount = grouped.max()

            return (
                f"{product} is the top-selling product "
                f"with sales of ₹{amount:,.2f}."
            )

        return "Product or Sales information is unavailable."

    # Best performing region
    elif "region" in question:

        if sales_col and region_col:
            grouped = df.groupby(region_col)[sales_col].sum()
            region = grouped.idxmax()
            amount = grouped.max()

            return (
                f"{region} is the highest-performing region "
                f"with sales of ₹{amount:,.2f}."
            )

        return "Region or Sales information is unavailable."

    # Total quantity
    elif any(word in question for word in ["quantity", "units sold"]):

        if quantity_col:
            total = df[quantity_col].sum()
            return f"Total quantity sold is {total} units."

        return "I couldn't find a Quantity column."

    # Total orders / records
    elif any(word in question for word in ["total orders", "number of orders", "total records"]):

        return f"The dataset contains {len(df)} records."

    # Dataset information
    elif any(word in question for word in ["columns", "dataset information", "dataset details"]):

        return (
            f"Your dataset contains {len(df)} records "
            f"and {len(df.columns)} columns: "
            f"{', '.join(map(str, df.columns))}."
        )

    else:
        return (
            "I can answer questions about total sales, profit, "
            "average sales, top products, regions, quantity, "
            "orders and dataset information. "
            "Please try one of these questions."
        )
