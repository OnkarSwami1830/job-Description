"""Text normalization helpers for job descriptions."""

import re


def preprocess(text: str) -> str:
    """Normalize a job description while retaining common skill symbols."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
