"""FastAPI service for real-time job description analysis."""

import json
import hashlib
import hmac
import os
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from dotenv import load_dotenv

from .extractors import analyze_text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).resolve().parent / ".env")
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

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "talentlens")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "local-development-secret-change-me").encode()
mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
database = mongo_client[MONGODB_DATABASE]
users_collection = database.users
jobs_collection = database.jobs
try:
    users_collection.create_index([("email", ASCENDING)], unique=True)
except PyMongoError:
    pass


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


class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class ResumeReviewRequest(BaseModel):
    resume: str = Field(min_length=40, max_length=100_000)
    job_description: str | None = Field(default=None, max_length=100_000)


def database_or_reject():
    try:
        mongo_client.admin.command("ping")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable. Set MONGODB_URI and start the server.") from exc
    return database


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$", 1)
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def create_token(user_id: str) -> str:
    payload = f"{user_id}.{int(time.time()) + 86400}"
    signature = hmac.new(TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_id, expires, signature = authorization[7:].split(".", 2)
        payload = f"{user_id}.{expires}"
        valid = hmac.compare_digest(signature, hmac.new(TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest())
        if not valid or int(expires) < time.time():
            raise ValueError
        user = database_or_reject().users.find_one({"_id": user_id}, {"password_hash": 0})
    except (ValueError, PyMongoError):
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def analyze_or_reject(text: str) -> dict:
    if not text.strip():
        raise HTTPException(status_code=422, detail="Job description cannot be empty")
    return analyze_text(text, TAXONOMY)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register")
def register(request: AuthRequest) -> dict:
    db = database_or_reject()
    email = request.email.strip().lower()
    user = {"_id": str(uuid4()), "email": email, "password_hash": hash_password(request.password), "created_at": datetime.now(timezone.utc)}
    try:
        db.users.insert_one(user)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
    return {"token": create_token(user["_id"]), "user": {"id": user["_id"], "email": email}}


@app.post("/auth/login")
def login(request: AuthRequest) -> dict:
    db = database_or_reject()
    user = db.users.find_one({"email": request.email.strip().lower()})
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user["_id"]), "user": {"id": user["_id"], "email": user["email"]}}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> dict:
    return analyze_or_reject(request.job_description)


@app.post("/improve")
def improve(request: ImproveRequest, user: dict = Depends(current_user)) -> dict:
    analysis = analyze_or_reject(request.job_description)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini is not configured. Set GEMINI_API_KEY in backend/.env.")
    prompt = f"""Rewrite this job description into polished, inclusive, recruiter-ready copy.
Keep all accurate facts from the original. Improve clarity and structure. Do not invent a company, salary, location, benefits, or requirements.
Return only the rewritten job description with headings for Summary, Responsibilities, Required Skills, Qualifications, and Benefits where supported.

Original job description:
{request.job_description}

Extracted role and signals:
{json.dumps(analysis, ensure_ascii=True)}"""
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=" + api_key
    try:
        request_obj = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            data = json.loads(response.read().decode())
        generated = data["candidates"][0]["content"]["parts"][0]["text"]
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Gemini could not regenerate the JD. Check the API key and quota.") from exc
    return {"analysis": analysis, "improved_description": generated, "generated_sections": analysis["missing_sections"]}


@app.post("/resume/review")
def review_resume(request: ResumeReviewRequest, user: dict = Depends(current_user)) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini is not configured. Set GEMINI_API_KEY in backend/.env.")
    job_context = request.job_description or "No job description was provided; review the resume on its own merits."
    prompt = f"""You are an expert recruiter. Review the resume below against the job description.
Return concise plain text with exactly these headings:
SUMMARY
STRENGTHS
GAPS
RECOMMENDATIONS
RESUME-READY SUMMARY

Job description:
{job_context}

Resume:
{request.resume}"""
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=" + api_key
    try:
        request_obj = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            data = json.loads(response.read().decode())
        summary = data["candidates"][0]["content"]["parts"][0]["text"]
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Gemini could not review the resume. Check the API key and quota.") from exc
    return {"review": summary}


@app.get("/jobs")
def list_jobs(user: dict = Depends(current_user)) -> list[dict]:
    return [{key: value for key, value in job.items() if key != "_id"} for job in jobs_collection.find({"user_id": user["_id"]})]


@app.get("/jobs/{job_id}")
def get_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    job = jobs_collection.find_one({"id": job_id, "user_id": user["_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs", status_code=201)
def save_job(request: AnalyzeRequest, user: dict = Depends(current_user)) -> dict:
    analysis = analyze_or_reject(request.job_description)
    job_id = str(uuid4())
    job = {"id": job_id, "user_id": user["_id"], **analysis, "job_description": request.job_description, "improved_description": None, "created_at": datetime.now(timezone.utc).isoformat()}
    jobs_collection.insert_one(job)
    return {key: value for key, value in job.items() if key != "user_id"}


@app.put("/jobs/{job_id}")
def update_job(job_id: str, update: JobUpdate, user: dict = Depends(current_user)) -> dict:
    job = jobs_collection.find_one({"id": job_id, "user_id": user["_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    changes = {}
    if update.job_description:
        changes.update(analyze_or_reject(update.job_description))
        changes["job_description"] = update.job_description
    if update.improved_description is not None:
        changes["improved_description"] = update.improved_description
    if changes:
        jobs_collection.update_one({"id": job_id, "user_id": user["_id"]}, {"$set": changes})
    return {key: value for key, value in jobs_collection.find_one({"id": job_id}, {"_id": 0}).items() if key != "user_id"}


@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, user: dict = Depends(current_user)) -> None:
    result = jobs_collection.delete_one({"id": job_id, "user_id": user["_id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Job not found")


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
