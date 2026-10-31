
from fastapi import FastAPI, UploadFile, File, HTTPException
from data_processing import load_dataset, clean_dataset
from analytics import generate_summary, calculate_sales

app = FastAPI(
    title="AI Business Intelligence Assistant",
    description="An AI-powered business data analytics API",
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
        df = clean_dataset(load_dataset(file))

        return {
            "filename": file.filename,
            "summary": generate_summary(df),
            "preview": df.head(5).fillna("").to_dict(orient="records")
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health():
    return {"status": "healthy"}
