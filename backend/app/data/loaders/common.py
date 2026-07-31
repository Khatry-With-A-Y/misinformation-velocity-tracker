"""Shared helpers for dataset loaders."""
from typing import Iterable, Optional


def first_present(row: dict, *candidates: str) -> Optional[str]:
    """Return the first non-empty value among candidate column names."""
    for c in candidates:
        if c in row and row[c] not in (None, "", "nan"):
            return row[c]
    return None


def normalize_domain(raw: Optional[str]) -> str:
    """Map dataset-specific category tags to our Source Router domains."""
    if not raw:
        return "other"
    r = str(raw).strip().lower()
    mapping = {
        "hlt": "health", "health": "health", "healthcare": "health",
        "medical": "health", "स्वास्थ्य": "health",
        "pol": "government", "politics": "government",
        "political": "government", "government": "government",
        "govt": "government", "राजनीति": "government",
        "election": "election", "निर्वाचन": "election",
        "finance": "finance", "financial": "finance",
        "economy": "finance", "money": "finance",
        "edu": "education", "education": "education", "educational": "education",
    }
    for key, val in mapping.items():
        if key in r:
            return val
    return "other"


def normalize_label(raw: Optional[str]) -> str:
    """Normalize REAL/FAKE/label-value fields to REAL | FAKE | UNVERIFIED."""
    if raw is None:
        return "UNVERIFIED"
    r = str(raw).strip().lower()
    if r in ("fake", "false", "1", "true_misinfo", "misinformation"):
        return "FAKE"
    if r in ("real", "true", "0", "accurate"):
        return "REAL"
    return "UNVERIFIED"


def take(iterable: Iterable, n: int) -> list:
    """Take up to n items from an iterable."""
    out = []
    for i, item in enumerate(iterable):
        if i >= n:
            break
        out.append(item)
    return out
