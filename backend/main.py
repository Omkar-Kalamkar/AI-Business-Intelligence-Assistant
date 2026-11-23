from pydantic import BaseModel
from ai_assistant import answer_question
import pandas as pd

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Query

from data_processing import load_dataset, clean_dataset
from analytics import generate_analysis, compare_sales
from anomaly_detection import detect_anomalies, detect_trend_anomalies
from root_cause import analyze_root_cause
from kpi_alerts import generate_kpi_alerts
from recommendations import generate_recommendations
import insight_history

import hashlib
import json
import uuid
from datetime import datetime, timezone

app = FastAPI(
    title="AI Business Intelligence Assistant",
    description="Analyze business datasets using Python and AI",
    version="1.1.0"
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
current_meta = None
current_analysis = None
current_insights = None


def _dataset_hash(df):
    hashed = pd.util.hash_pandas_object(df, index=True).values
    return hashlib.sha256(hashed.tobytes()).hexdigest()


class ChatRequest(BaseModel):
    question: str

class CompareRequest(BaseModel):
    dimension: str
    item1: str
    item2: str


@app.get("/")
def home():

    return {
        "message": "Welcome to AI Business Intelligence Assistant",
        "status": "Running"
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global current_df, current_meta, current_analysis, current_insights

    try:
        df = load_dataset(file)

        original_records = len(df)
        df = clean_dataset(df)

        current_df = df.copy()

        analysis = generate_analysis(df)
        current_analysis = analysis
        current_insights = None

        dataset_hash = _dataset_hash(df)
        current_meta = {
            "dataset_id": uuid.uuid4().hex,
            "filename": file.filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "record_count": int(len(df)),
            "dataset_hash": dataset_hash,
        }

        insight_history.save_insight(
            filename=file.filename,
            payload={"analysis": analysis},
            kind="upload_analysis",
            dataset_hash=dataset_hash,
            record_count=int(len(df)),
        )

        preview = json.loads(
            df.head(5).to_json(orient="records", date_format="iso")
        )

        return {
            "message": "Dataset analyzed successfully!",
            "filename": file.filename,
            "original_records": original_records,
            "cleaned_records": len(df),
            "analysis": analysis,
            "preview": preview,
            "dataset_id": current_meta["dataset_id"],
            "uploaded_at": current_meta["uploaded_at"]
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
            request.question,
            insights=current_insights
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


@app.post("/compare")
async def compare_dataset(request: CompareRequest):

    if current_df is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a dataset first."
        )

    try:
        if request.dimension.lower() not in ["product", "region"]:
            raise ValueError(
                "Dimension must be either product or region."
            )

        result = compare_sales(
            current_df,
            request.dimension,
            request.item1,
            request.item2
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


def _require_dataset():
    if current_df is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a dataset first."
        )


@app.get("/insights")
def business_insights(save: bool = Query(default=True)):
    global current_insights

    _require_dataset()

    try:
        df = current_df
        analysis = current_analysis or generate_analysis(df)

        anomalies = detect_anomalies(df)
        trends = detect_trend_anomalies(df)
        root_cause = analyze_root_cause(df, trends)
        alerts = generate_kpi_alerts(df)
        recommendations = generate_recommendations(
            analysis,
            anomalies=anomalies,
            trends=trends,
            root_cause=root_cause,
            alerts=alerts,
        )

        payload = {
            "dataset_id": current_meta["dataset_id"],
            "filename": current_meta["filename"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": analysis["summary"],
            "anomalies": anomalies,
            "trends": trends,
            "root_cause": root_cause,
            "kpi_alerts": alerts,
            "recommendations": recommendations,
        }

        insight_id = None
        if save:
            saved = insight_history.save_insight(
                filename=current_meta["filename"],
                payload=payload,
                kind="business_insights",
                dataset_hash=current_meta["dataset_hash"],
                record_count=current_meta["record_count"],
            )
            insight_id = saved["id"]

        payload["insight_id"] = insight_id
        current_insights = payload

        return payload

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/history")
def history_list(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    try:
        return insight_history.list_insights(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{insight_id}")
def history_detail(insight_id: int):
    try:
        result = insight_history.get_insight(insight_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Insight not found."
        )

    return result


@app.delete("/history/{insight_id}")
def history_delete(insight_id: int):
    try:
        deleted = insight_history.delete_insight(insight_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Insight not found."
        )

    return {"deleted": True, "id": insight_id}

