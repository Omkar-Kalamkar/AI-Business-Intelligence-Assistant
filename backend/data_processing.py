import io
import os
from pathlib import Path

import pandas as pd


MAX_UPLOAD_BYTES = int(
    os.environ.get("MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
)
MAX_DATASET_ROWS = int(os.environ.get("MAX_DATASET_ROWS", 100000))
MAX_DATASET_COLUMNS = int(os.environ.get("MAX_DATASET_COLUMNS", 200))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UploadTooLarge(ValueError):
    pass


def sanitize_filename(filename):
    if not filename:
        return "dataset"

    name = str(filename).replace("\\", "/").split("/")[-1]
    cleaned = []
    for character in name:
        if character.isprintable() and character not in '<>:"/\\|?*':
            cleaned.append(character)
        else:
            cleaned.append("_")

    result = "".join(cleaned).strip(" ._")
    return result[:120] or "dataset"


def validate_uploaded_file(filename, content):
    if not content:
        raise ValueError("The uploaded file is empty.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadTooLarge(
            "The uploaded file is too large. The maximum size is "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Please upload a CSV or Excel file.")

    if suffix == ".csv":
        if content.startswith(b"PK\x03\x04") or b"\x00" in content[:1024]:
            raise ValueError("The CSV file does not contain valid text data.")
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(
                "The CSV file could not be decoded as UTF-8 text."
            ) from error
    elif suffix == ".xlsx":
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("The Excel file is invalid or corrupted.")
    elif not content.startswith(b"\xd0\xcf\x11\xe0"):
        raise ValueError("The Excel file is invalid or corrupted.")


def load_dataset(file, content=None):
    filename = sanitize_filename(getattr(file, "filename", None))

    if content is None:
        reader = getattr(file, "file", file)
        content = reader.read(MAX_UPLOAD_BYTES + 1)

    validate_uploaded_file(filename, content)
    stream = io.BytesIO(content)

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(stream)
    else:
        df = pd.read_excel(stream)

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    if len(df) > MAX_DATASET_ROWS:
        raise ValueError(
            f"The dataset has too many rows. The maximum is "
            f"{MAX_DATASET_ROWS:,}."
        )

    if len(df.columns) > MAX_DATASET_COLUMNS:
        raise ValueError(
            f"The dataset has too many columns. The maximum is "
            f"{MAX_DATASET_COLUMNS}."
        )

    return df


def _unique_columns(columns):
    counts = {}
    result = []

    for column in columns:
        base = str(column).strip() or "column"
        count = counts.get(base, 0)
        result.append(base if count == 0 else f"{base}_{count}")
        counts[base] = count + 1

    return result


def clean_dataset(df):
    df = df.dropna(how="all")
    df = df.drop_duplicates()
    df.columns = _unique_columns(df.columns)

    if df.empty:
        raise ValueError("The uploaded dataset contains no usable records.")

    return df
