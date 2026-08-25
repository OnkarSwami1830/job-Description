"""FastAPI service for real-time job description analysis."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .extractors import analyze_text

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "data" / "skill_taxonomy.json").open(encoding="utf-8") as handle:
    TAXONOMY = json.load(handle)

app = FastAPI(title="AI Job Description Analyzer", version="1.0.0")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=100_000)


class AnalyzeResponse(BaseModel):
    job_title: str
    company: str
    department: str
    location: str
    work_mode: str
    employment_type: str
    job_role: str
    experience: str
    education: str
    salary: str
    technical_skills: list[str]
    preferred_skills: list[str]
    soft_skills: list[str]
    skills: list[str]
    skills_by_category: dict[str, list[str]]
    responsibilities: list[str]
    qualifications: list[str]
    benefits: list[str]
    notice_period: str
    hiring_priority: str
    missing_sections: list[str]
    quality: dict[str, float]
    jd_score: float
    ai_recommendations: list[str]
    confidence: float


class ImproveRequest(AnalyzeRequest):
    pass


class JobUpdate(BaseModel):
    job_description: str | None = Field(default=None, min_length=20, max_length=100_000)
    improved_description: str | None = None


JOBS: dict[str, dict] = {}


def analyze_or_reject(text: str) -> dict:
    if not text.strip():
        raise HTTPException(status_code=422, detail="Job description cannot be empty")
    return analyze_text(text, TAXONOMY)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> dict:
    return analyze_or_reject(request.job_description)


@app.post("/improve")
def improve(request: ImproveRequest) -> dict:
    analysis = analyze_or_reject(request.job_description)
    generated = _improve_description(request.job_description, analysis)
    return {"analysis": analysis, "improved_description": generated, "generated_sections": analysis["missing_sections"]}


@app.get("/jobs")
def list_jobs() -> list[dict]:
    return list(JOBS.values())


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]


@app.post("/jobs", status_code=201)
def save_job(request: AnalyzeRequest) -> dict:
    analysis = analyze_or_reject(request.job_description)
    job_id = str(uuid4())
    JOBS[job_id] = {"id": job_id, **analysis, "job_description": request.job_description, "improved_description": None, "created_at": datetime.now(timezone.utc).isoformat()}
    return JOBS[job_id]


@app.put("/jobs/{job_id}")
def update_job(job_id: str, update: JobUpdate) -> dict:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    if update.job_description:
        JOBS[job_id].update(analyze_or_reject(update.job_description))
        JOBS[job_id]["job_description"] = update.job_description
    if update.improved_description is not None:
        JOBS[job_id]["improved_description"] = update.improved_description
    return JOBS[job_id]


@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> None:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    del JOBS[job_id]


@app.post("/upload", response_model=AnalyzeResponse)
async def upload(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    content = await file.read()
    if suffix == ".txt":
        text = content.decode("utf-8", errors="replace")
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc
    elif suffix == ".docx":
        try:
            from docx import Document
            import io
            text = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read DOCX: {exc}") from exc
    else:
        raise HTTPException(status_code=415, detail="Upload a PDF, DOCX, or TXT file")
    return analyze_or_reject(text)


def _improve_description(original: str, analysis: dict) -> str:
    role = analysis["job_role"]
    skills = ", ".join(analysis["technical_skills"][:8]) or "relevant technical skills"
    additions = [
        f"## Job Summary\nWe are seeking a {role} to deliver reliable, high-impact work with a collaborative team.",
        f"## Responsibilities\n- Design, build, test, and maintain solutions for the {role} team.\n- Collaborate with stakeholders to deliver measurable outcomes.",
        f"## Required Skills\n- Demonstrated experience with {skills}.",
        "## Benefits\n- Competitive compensation, learning support, and a supportive working environment.",
        "## Equal Opportunity\nWe are committed to building an inclusive workplace and consider qualified candidates without regard to background or identity.",
    ]
    return original.rstrip() + "\n\n" + "\n\n".join(additions)
