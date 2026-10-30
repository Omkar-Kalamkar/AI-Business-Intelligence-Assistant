
import pandas as pd


def load_dataset(file):
    """Load CSV or Excel business datasets."""

    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(file.file)

    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file.file)

    else:
        raise ValueError("Only CSV and Excel files are supported.")

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    return df


def clean_dataset(df):
    """Clean missing values and duplicate records."""

    df = df.drop_duplicates()
    df = df.dropna(how="all")

    return df
