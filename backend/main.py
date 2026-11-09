from pydantic import BaseModel
from ai_assistant import answer_question
import pandas as pd

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException

from data_processing import load_dataset, clean_dataset
from analytics import generate_analysis

import json

app = FastAPI(
    title="AI Business Intelligence Assistant",
    description="Analyze business datasets using Python and AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store the latest uploaded dataset in memory
current_df = None


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():

    return {
        "message": "Welcome to AI Business Intelligence Assistant",
        "status": "Running"
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global current_df

    try:
        df = load_dataset(file)

        original_records = len(df)
        df = clean_dataset(df)

        current_df = df.copy()

        analysis = generate_analysis(df)

        preview = json.loads(
            df.head(5).to_json(orient="records")
        )

        return {
            "message": "Dataset analyzed successfully!",
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


@app.post("/ask")
async def ask_question(request: ChatRequest):

    if current_df is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a dataset first."
        )

    try:
        answer = answer_question(
            current_df,
            request.question
        )

        return {
            "question": request.question,
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
