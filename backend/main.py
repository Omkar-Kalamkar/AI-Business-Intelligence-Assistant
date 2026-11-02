
from fastapi import FastAPI, UploadFile, File, HTTPException

from data_processing import load_dataset, clean_dataset
from analytics import generate_analysis

import json

app = FastAPI(
    title="AI Business Intelligence Assistant",
    description="Analyze business datasets using Python and AI",
    version="1.0.0"
)


@app.get("/")
def home():

    return {
        "message": "Welcome to AI Business Intelligence Assistant",
        "status": "Running"
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):

    try:

        df = load_dataset(file)

        original_records = len(df)
        df = clean_dataset(df)

        analysis = generate_analysis(df)

        preview = json.loads(
            df.head(5).to_json(orient="records")
        )

        return {
            "message": "Dataset uploaded and analyzed successfully!",
            "filename": file.filename,
            "original_records": original_records,
            "cleaned_records": len(df),
            "analysis": analysis,
            "preview": preview
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }
