
import pandas as pd


def load_dataset(file):
    """Load CSV or Excel files."""

    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(file.file)

    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file.file)

    else:
        raise ValueError("Please upload a CSV or Excel file.")

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    return df


def clean_dataset(df):
    """Clean the uploaded dataset."""

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove duplicate records
    df = df.drop_duplicates()

    # Remove unnecessary spaces from column names
    df.columns = df.columns.astype(str).str.strip()

    return df
