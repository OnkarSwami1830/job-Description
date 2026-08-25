"""Live analyzer adapter built on the project's shared extraction rules."""

import re
from typing import Any

from src.extractors import extract_education, extract_experience, extract_role, extract_skills

NORMALIZATIONS = {
    "JS": "JavaScript", "Postgres": "PostgreSQL", "Spring": "Spring Boot",
    "ML": "Machine Learning", "K8s": "Kubernetes", "ReactJS": "React",
}


def extract_salary(text: str) -> str:
    patterns = [
        r"(?:₹|rs\.?|inr|\$|usd)\s?[\d,]+(?:\.\d+)?(?:\s?[-–]\s?(?:₹|rs\.?|inr|\$|usd)?\s?[\d,]+(?:\.\d+)?)?\s*(?:per\s+(?:month|year)|lpa|pa)?",
        r"\b\d+(?:\.\d+)?\s?(?:[-–]|to)\s?\d+(?:\.\d+)?\s?(?:lpa|lakhs?(?:\s+per\s+annum)?)\b",
        r"\b\d+(?:\.\d+)?\s?(?:lpa|lakhs?(?:\s+per\s+annum)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip(" .")
    return "Not Mentioned"


def analyze_text(text: str, taxonomy: dict[str, list[str]]) -> dict[str, Any]:
    role = extract_role(text)
    skills_by_category = extract_skills(text, taxonomy)
    skills = [skill for category_skills in skills_by_category.values() for skill in category_skills]
    experience = extract_experience(text)
    education = extract_education(text)
    normalized_skills = [NORMALIZATIONS.get(skill, skill) for skill in skills]
    technical = [skill for skill in normalized_skills if skill not in taxonomy.get("Soft Skills", [])]
    soft = [skill for skill in normalized_skills if skill in taxonomy.get("Soft Skills", [])]
    missing_sections = [section for section, present in {
        "Job Summary": len(text.split()) > 35,
        "Responsibilities": bool(re.search(r"responsibilit|you will|duties|build|develop|manage", text, re.I)),
        "Qualifications": bool(re.search(r"qualification|degree|education|experience", text, re.I)),
        "Benefits": bool(re.search(r"benefit|insurance|leave|bonus|allowance", text, re.I)),
        "Company Culture": bool(re.search(r"culture|mission|values|team", text, re.I)),
    }.items() if not present]
    completeness = round(max(0, 100 - len(missing_sections) * 14), 1)
    clarity = round(min(100, 55 + (10 if len(text.split()) > 80 else 0) + (10 if "." in text else 0)), 1)
    diversity = 90.0 if re.search(r"equal opportunity|inclusive|diversity", text, re.I) else 58.0
    skill_coverage = round(min(100, len(technical) * 12 + len(soft) * 8), 1)
    jd_score = round(completeness * .4 + skill_coverage * .25 + clarity * .2 + diversity * .15, 1)
    signals = sum(bool(value) for value in (role != "Unknown", skills, experience != "Not Mentioned", education != "Not Mentioned"))
    confidence = round(min(99.0, 50.0 + len(skills) * 4.0 + signals * 5.0), 1)
    return {
        "job_title": role,
        "company": _first_match(text, [r"(?:at|for|with)\s+([A-Z][\w& ]{2,30})", r"([A-Z][\w]+) is hiring"]),
        "department": _first_match(text, [r"(?:department|team)[:\s]+([\w &-]+)"]) or "Not Mentioned",
        "location": _first_match(text, [r"(?:location|based in|office in)[:\s]+([\w ,&-]+)"]) or "Not Mentioned",
        "work_mode": _first_match(text, [r"\b(remote|hybrid|onsite|on-site)\b"]).title() or "Not Mentioned",
        "employment_type": _first_match(text, [r"\b(full-time|part-time|contract|internship|permanent)\b"]).title() or "Not Mentioned",
        "job_role": role,
        "experience": experience,
        "education": education,
        "salary": extract_salary(text),
        "technical_skills": technical,
        "preferred_skills": [],
        "soft_skills": soft,
        "skills": normalized_skills,
        "skills_by_category": skills_by_category,
        "responsibilities": _list_after_heading(text, "responsibilit"),
        "qualifications": _list_after_heading(text, "qualification"),
        "benefits": _list_after_heading(text, "benefit"),
        "notice_period": _first_match(text, [r"notice period[:\s]+([^,.\n]+)"]) or "Not Mentioned",
        "hiring_priority": "High" if re.search(r"urgent|immediately|asap", text, re.I) else "Standard",
        "missing_sections": missing_sections,
        "quality": {"completeness": completeness, "skill_coverage": skill_coverage, "clarity": clarity, "diversity_inclusion": diversity, "overall": jd_score},
        "jd_score": jd_score,
        "ai_recommendations": _recommendations(missing_sections, technical, soft),
        "confidence": confidence,
    }


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1) if match.lastindex else match.group(0)).strip(" .,:;")
    return ""


def _list_after_heading(text: str, heading: str) -> list[str]:
    match = re.search(heading + r"[^:\n]*[:\n](.*?)(?:\n\s*\n|$)", text, re.I | re.S)
    if not match:
        return []
    return [line.strip(" -*\t") for line in match.group(1).splitlines() if line.strip(" -*\t")][:8]


def _recommendations(missing: list[str], technical: list[str], soft: list[str]) -> list[str]:
    recommendations = [f"Add a {section.lower()} section" for section in missing]
    if len(technical) < 3:
        recommendations.append("Specify the core technical skills required for success")
    if not soft:
        recommendations.append("Include measurable soft-skill expectations")
    return recommendations[:6]
