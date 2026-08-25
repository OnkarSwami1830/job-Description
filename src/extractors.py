"""Rule-based extractors used by the batch pipeline."""

import re
from typing import Any

from .preprocess import preprocess

DEFAULT_ROLES = [
    "data scientist", "machine learning engineer", "full stack developer",
    "backend developer", "frontend developer", "software engineer",
    "data engineer", "devops engineer", "qa engineer", "test engineer",
    "android developer", "ios developer", "flutter developer", "django developer",
    "java developer", "javascript developer", "python developer", "web developer",
]


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])", text) is not None


def extract_role(description: str, title: str = "", roles: list[str] | None = None) -> str:
    """Return the best role from the source title or description."""
    candidates = roles or DEFAULT_ROLES
    combined = preprocess(f"{title} {description}")
    for role in sorted(candidates, key=len, reverse=True):
        if _contains(combined, role):
            return role.title()
    return title.strip() or "Unknown"


def extract_skills(description: str, taxonomy: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized = preprocess(description)
    found: dict[str, list[str]] = {}
    for category, skills in taxonomy.items():
        matches = [skill for skill in skills if _contains(normalized, preprocess(skill))]
        if matches:
            found[category] = matches
    return found


def extract_experience(description: str) -> str:
    pattern = r"\b\d+\+?\s*(?:-|to|–|—)?\s*\d*\+?\s*(?:years?|yrs?)\b"
    match = re.search(pattern, description, re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(0)).strip() if match else "Not Mentioned"


def extract_education(description: str) -> str:
    patterns = [
        r"\b(?:b\.?\s?tech|bachelor(?:'s)?|b\.?\s?e\.?|m\.?\s?tech|master(?:'s)?|m\.?\s?e\.?|ph\.?d|mba|bca|mca)\b(?:\s+degree)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            value = re.sub(r"\s+", " ", match.group(0)).strip(" :-.,")
            return value
    return "Not Mentioned"


def extract_record(row: dict[str, Any], taxonomy: dict[str, list[str]]) -> dict[str, Any]:
    title = (row.get("Job Title") or row.get("job_role") or "").strip()
    description = (row.get("Job Description") or row.get("job_description") or "").strip()
    return {
        "job_id": row.get("job_id") or row.get("" , ""),
        "job_title": title,
        "company": (row.get("company") or "").strip(),
        "job_role": extract_role(description, title),
        "experience": (row.get("experience") or extract_experience(description)).strip(),
        "education": (row.get("education") or extract_education(description)).strip(),
        "skills": extract_skills(description, taxonomy),
    }
