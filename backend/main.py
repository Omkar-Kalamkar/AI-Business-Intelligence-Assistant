import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ai_assistant import answer_question
from analytics import generate_analysis, compare_sales
from anomaly_detection import detect_anomalies, detect_trend_anomalies
from data_processing import (
    MAX_UPLOAD_BYTES,
    UploadTooLarge,
    clean_dataset,
    load_dataset,
    sanitize_filename,
)
from excel_report import build_excel_report
from kpi_alerts import generate_kpi_alerts
from recommendations import generate_recommendations
from report import build_pdf_report
from reporting import (
    ReportValidationError,
    build_report_payload,
    validate_report_payload,
)
from root_cause import analyze_root_cause
import insight_history


logger = logging.getLogger("bi_assistant")


def _cors_origins():
    configured = os.environ.get("CORS_ALLOW_ORIGINS")
    if configured:
        return [
            origin.strip()
            for origin in configured.split(",")
            if origin.strip() and origin.strip() != "*"
        ]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app = FastAPI(
    title="AI Business Intelligence Assistant",
    description="Analyze business datasets using Python and AI",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Store the latest uploaded dataset in memory
current_df = None
current_meta = None
current_analysis = None
current_insights = None


def _dataset_hash(df):
    try:
        hashed = pd.util.hash_pandas_object(df, index=True).values
        digest = hashlib.sha256(hashed.tobytes()).hexdigest()
    except (TypeError, ValueError):
        payload = df.to_json(orient="records", date_format="iso")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest


def _pdf_filename(filename, insight_id=None):
    base = os.path.splitext(sanitize_filename(filename))[0]
    safe = "".join(
        character
        if character.isascii() and (character.isalnum() or character in "._-")
        else "_"
        for character in base
    )
    safe = safe.strip("._") or "insight"
    suffix = f"_{insight_id}" if insight_id else ""
    return f"{safe[:70]}{suffix}.pdf"


def _report_filename(filename, extension, report_id=None):
    base = os.path.splitext(sanitize_filename(filename))[0]
    safe = "".join(
        character
        if character.isascii() and (character.isalnum() or character in "._-")
        else "_"
        for character in base
    )
    safe = safe.strip("._") or "report"
    suffix = f"_{report_id}" if report_id else ""
    return f"{safe[:60]}{suffix}.{extension}"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CompareRequest(BaseModel):
    dimension: str = Field(min_length=1, max_length=50)
    item1: str = Field(min_length=1, max_length=200)
    item2: str = Field(min_length=1, max_length=200)


class ReportRequest(BaseModel):
    title: str = Field(
        default="Business Intelligence Report",
        min_length=1,
        max_length=120,
    )
    notes: str = Field(default="", max_length=1000)


@app.get("/")
def home():

    return {
        "message": "Welcome to AI Business Intelligence Assistant",
        "status": "Running"
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global current_df, current_meta, current_analysis, current_insights

    filename = sanitize_filename(file.filename)

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise UploadTooLarge(
                "The uploaded file is too large. The maximum size is "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )

        df = load_dataset(file, content=content)

        original_records = len(df)
        df = clean_dataset(df)

        current_df = df.copy()

        analysis = generate_analysis(df)
        current_analysis = analysis
        current_insights = None

        dataset_hash = _dataset_hash(df)
        current_meta = {
            "dataset_id": uuid.uuid4().hex,
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "record_count": int(len(df)),
            "dataset_hash": dataset_hash,
        }

        insight_history.save_insight(
            filename=filename,
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
            "filename": filename,
            "original_records": original_records,
            "cleaned_records": len(df),
            "analysis": analysis,
            "preview": preview,
            "dataset_id": current_meta["dataset_id"],
            "uploaded_at": current_meta["uploaded_at"]
        }

    except UploadTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except HTTPException:
        raise

    except Exception:
        logger.exception("Dataset upload failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to upload and analyze the dataset."
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

    except HTTPException:
        raise

    except Exception:
        logger.exception("Question answering failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to answer the question right now."
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

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except HTTPException:
        raise

    except Exception:
        logger.exception("Dataset comparison failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to compare the selected items right now."
        )


def _require_dataset():
    if current_df is None or current_meta is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a dataset first."
        )


def _build_insights(save=True):
    global current_insights

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
        "insights": analysis.get("insights", []),
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


def _report_response(payload, filename):
    pdf = build_pdf_report(payload, filename=filename)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


def _report_payload_from_record(record):
    payload = dict(record.get("payload") or {})
    if "anomalies" in payload:
        return payload

    analysis = payload.get("analysis") or {}
    return {
        "filename": record.get("filename"),
        "generated_at": record.get("created_at"),
        "summary": analysis.get("summary", {}),
        "insights": analysis.get("insights", []),
        "recommendations": analysis.get("recommendations", []),
    }


@app.get("/insights")
def business_insights(save: bool = Query(default=True)):
    _require_dataset()

    try:
        return _build_insights(save=save)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Insight generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate business insights right now."
        )


@app.get("/report")
def download_report(save: bool = Query(default=False)):
    _require_dataset()

    try:
        payload = current_insights or _build_insights(save=save)
        filename = _pdf_filename(
            current_meta["filename"], payload.get("insight_id")
        )
        return _report_response(payload, filename)

    except HTTPException:
        raise

    except Exception:
        logger.exception("PDF report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report right now."
        )


@app.get("/report/{insight_id}")
def download_saved_report(insight_id: int):
    try:
        record = insight_history.get_insight(insight_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Insight not found."
            )

        payload = _report_payload_from_record(record)
        filename = _pdf_filename(record["filename"], insight_id)
        return _report_response(payload, filename)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Saved PDF report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report right now."
        )


@app.get("/history")
def history_list(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    try:
        return insight_history.list_insights(limit=limit, offset=offset)
    except Exception:
        logger.exception("History listing failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load insight history right now."
        )


@app.get("/history/{insight_id}")
def history_detail(insight_id: int):
    try:
        result = insight_history.get_insight(insight_id)
    except Exception:
        logger.exception("History detail lookup failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load this insight right now."
        )

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
    except Exception:
        logger.exception("History deletion failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to delete this insight right now."
        )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Insight not found."
        )

    return {"deleted": True, "id": insight_id}


def _build_current_report_payload(request=None):
    insights = current_insights or _build_insights(save=True)
    return build_report_payload(
        current_analysis,
        insights,
        filename=current_meta["filename"],
        dataset_id=current_meta["dataset_id"],
        title=request.title if request else None,
        notes=request.notes if request else None,
    )


def _export_response(payload, filename, extension):
    validate_report_payload(payload)

    if extension == "pdf":
        content = build_pdf_report(payload, filename=filename)
        media_type = "application/pdf"
    else:
        content = build_excel_report(payload, filename=filename)
        media_type = (
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


def _get_stored_report(report_id):
    record = insight_history.get_insight(report_id)

    if record is None or record.get("kind") != "business_report":
        raise HTTPException(status_code=404, detail="Report not found.")

    validate_report_payload(record["payload"])
    return record


@app.post("/reports", status_code=201)
def create_report(request: ReportRequest | None = None):
    _require_dataset()

    try:
        payload = _build_current_report_payload(request)
        saved = insight_history.save_insight(
            filename=current_meta["filename"],
            payload=payload,
            kind="business_report",
            dataset_hash=current_meta["dataset_hash"],
            record_count=current_meta["record_count"],
        )
        result = dict(saved)
        result["report"] = payload
        return result

    except HTTPException:
        raise

    except (ReportValidationError, ValueError) as error:
        logger.exception("Report validation failed")
        raise HTTPException(
            status_code=400,
            detail="The generated report data could not be validated.",
        ) from error

    except Exception:
        logger.exception("Report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the report right now."
        )


@app.get("/reports")
def list_reports(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    try:
        return insight_history.list_insights(
            limit=limit, offset=offset, kind="business_report"
        )
    except Exception:
        logger.exception("Report history listing failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load report history right now."
        )


@app.get("/reports/current/pdf")
def download_current_report_pdf():
    _require_dataset()

    try:
        payload = _build_current_report_payload()
        filename = _report_filename(current_meta["filename"], "pdf")
        return _export_response(payload, filename, "pdf")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Current PDF report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report right now."
        )


@app.get("/reports/current/excel")
def download_current_report_excel():
    _require_dataset()

    try:
        payload = _build_current_report_payload()
        filename = _report_filename(current_meta["filename"], "xlsx")
        return _export_response(payload, filename, "excel")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Current Excel report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the Excel report right now."
        )


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    try:
        return _get_stored_report(report_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Report lookup failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load this report right now."
        )


@app.delete("/reports/{report_id}")
def delete_report(report_id: int):
    try:
        _get_stored_report(report_id)
        deleted = insight_history.delete_insight(report_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Report deletion failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to delete this report right now."
        )

    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")

    return {"deleted": True, "id": report_id}


@app.get("/reports/{report_id}/pdf")
def download_report_pdf(report_id: int):
    try:
        record = _get_stored_report(report_id)
        filename = _report_filename(record["filename"], "pdf", report_id)
        return _export_response(record["payload"], filename, "pdf")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Saved PDF report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report right now."
        )


@app.get("/reports/{report_id}/excel")
def download_report_excel(report_id: int):
    try:
        record = _get_stored_report(report_id)
        filename = _report_filename(record["filename"], "xlsx", report_id)
        return _export_response(record["payload"], filename, "excel")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Saved Excel report generation failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the Excel report right now."
        )

