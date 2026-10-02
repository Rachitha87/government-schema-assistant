"""
Profile extraction from free text.

Runs inside the "User Profile Agent". It is deliberately **rule based**:
eligibility inputs must be reproducible, so a language model is never allowed
to decide somebody's age, income or category. When a fresher reads the code
they can verify every rule by eye.

Example
-------
    parse_profile_from_text(
        "I am a 21-year-old student from Karnataka pursuing MCA. "
        "My family income is Rs 2 lakh per year."
    )
"""

from __future__ import annotations

import re
from typing import Optional

from models.profile import UserProfile
from utils.normalize import (
    INDIAN_STATES,
    normalise_category,
    normalise_disability_status,
    normalise_education_level,
    normalise_gender,
    normalise_state,
    normalise_student_status,
    parse_income,
)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
AGE_PATTERNS = [
    re.compile(r"\b(\d{1,2})\s*[- ]?\s*(?:years?|yrs?)\s*[- ]?\s*old\b", re.IGNORECASE),
    re.compile(r"\b(?:age|aged)\s*[:=]?\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\bi\s*(?:am|'m| am)\s*(\d{1,2})\b", re.IGNORECASE),
]

CATEGORY_RE = re.compile(r"\b(scheduled\s+caste|scheduled\s+tribe|obc|other\s+backward|ebc|dnt|sc|st|general)\b", re.IGNORECASE)

GENDER_RE = re.compile(r"\b(female|male|girl|boy|woman|man|women|girls)\b", re.IGNORECASE)

DISABILITY_RE = re.compile(
    r"\b(differently\s*abled|disabilit(?:y|ed)|divyang|physically\s+challenged|"
    r"visually\s+impaired|hearing\s+impaired|wheel\s?chair|special\s+abilit(?:y|ies)|"
    r"orthopedically\s+challenged|intellectually\s+challenged)\b",
    re.IGNORECASE,
)

STATUS_RE = re.compile(
    r"\b(full[\s-]?time|part[\s-]?time|working|employed|job|unemployed|"
    r"looking\s+for\s+(?:a\s+)?job|student|school\s*goer)\b",
    re.IGNORECASE,
)

PERCENTAGE_RE = re.compile(
    r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|per\s*cent)\b", re.IGNORECASE
)

# Course / qualification words we can recognise, mapped to the course name.
COURSE_TOKENS: dict[str, str] = {
    "mca": "MCA",
    "mba": "MBA",
    "mtech": "M.Tech",
    "mtech": "M.Tech",
    "msc": "M.Sc",
    "mcom": "M.Com",
    "ma": "MA",
    "btech": "B.Tech",
    "btech": "B.Tech",
    "bca": "BCA",
    "bca": "BCA",
    "bsc": "B.Sc",
    "bcom": "B.Com",
    "ba": "BA",
    "bba": "BBA",
    "bpharm": "B.Pharm",
    "bs": "B.S",
    "mcs": "MCS",
    "phd": "PhD",
    "mphil": "MPhil",
    "iti": "ITI",
    "polytechnic": "Diploma",
    "diploma": "Diplama",
}

COURSE_RE = re.compile(
    r"\b(mca|mba|m\.?tech|msc|m\.sc|mcom|m\.com|b\.?tech|be|bca|b\.?sc|b\.?com|bpharm|bba|mphil|phd|iti|polytechnic|diploma|bachelor(?:'s)?|master(?:'s)?|graduation|undergraduate|postgraduate)\b",
    re.IGNORECASE,
)

# Education level cues that normalise_education_level() cannot see on its own.
LEVEL_CUES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(class\s*(?:1?\s*-?\s*)?(?:9|10|11|12)(?:th)?)\b", re.IGNORECASE), "Class 9-12"),
    (re.compile(r"\b(10th|12th|intermediate|higher\s+secondary|high\s+school|secondary\s+school)\b", re.IGNORECASE), "Class 9-12"),
    (re.compile(r"\b(middle\s+school|primary\s+school|class\s*[1-8])\b", re.IGNORECASE), "School (Class 1-8)"),
    (re.compile(r"\b(post\s*graduation|postgraduate|post\s*graduate|pg|masters|master's|master\s+degree|mca|mba|m\.?tech)\b", re.IGNORECASE), "Postgraduate"),
    (re.compile(r"\b(under\s*graduation|undergraduate|ug|bachelor(?:'s)?|graduation|b\.?tech|bca|b\.?sc)\b", re.IGNORECASE), "Undergraduate"),
    (re.compile(r"\b(phd|doctorate|doctoral|mphil)\b", re.IGNORECASE), "MPhil/PhD"),
    (re.compile(r"\b(diploma|polytechnic|iti)\b", re.IGNORECASE), "Diploma"),
]


# ---------------------------------------------------------------------------
# Individual extractors
# ---------------------------------------------------------------------------
def extract_age(text: str) -> Optional[int]:
    for pattern in AGE_PATTERNS:
        match = pattern.search(text)
        if match:
            age = int(match.group(1))
            if 5 <= age <= 100:
                return age
    return None


def extract_state(text: str) -> Optional[str]:
    lowered = text.lower()
    # Longest names first so "Tamil Nadu" is not read as "Tamil".
    for state in sorted(INDIAN_STATES, key=len, reverse=True):
        pattern = r"\b" + re.escape(state.lower()).replace(r"\ ", r"[\s-]+") + r"\b"
        if re.search(pattern, lowered):
            return normalise_state(state)
    return None


def extract_category(text: str) -> Optional[str]:
    # "SC/ST" or "OBC/SC" should not pick only the first token.
    if re.search(r"\b(sc\s*/\s*st|st\s*/\s*sc)\b", text, re.IGNORECASE):
        return "SC"
    match = CATEGORY_RE.search(text)
    if not match:
        return None
    token = re.sub(r"\s+", " ", match.group(1).lower())
    return normalise_category(token)


def extract_gender(text: str) -> Optional[str]:
    match = GENDER_RE.search(text)
    return normalise_gender(match.group(1)) if match else None


def extract_education_level(text: str) -> Optional[str]:
    for pattern, level in LEVEL_CUES:
        if pattern.search(text):
            if level == "Class 9-12":
                return normalise_education_level("class 9-12") or level
            return level
    match = re.search(r"\b(class\s*\d{1,2}(?:th)?)\b", text, re.IGNORECASE)
    if match:
        return normalise_education_level(match.group(1))
    return None


def extract_course(text: str) -> Optional[str]:
    match = COURSE_RE.search(text)
    if not match:
        return None
    token = match.group(1).lower().replace(".", "").replace("-", "")
    return COURSE_TOKENS.get(token) or match.group(1).upper()


def extract_student_status(text: str) -> Optional[str]:
    match = STATUS_RE.search(text)
    if not match:
        return None
    token = match.group(1).lower()
    if token in {"student", "school goer"}:
        return "Full-time"
    return normalise_student_status(token)


def extract_disability(text: str) -> Optional[str]:
    if DISABILITY_RE.search(text):
        return "Yes"
    if re.search(r"\bnot\s+(?:a\s+)?(?:differently\s*abled|disabled)\b", text, re.IGNORECASE):
        return "No"
    return None


def extract_percentage(text: str) -> Optional[float]:
    match = PERCENTAGE_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 <= value <= 100 else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_profile_from_text(text: str, base: Optional[UserProfile] = None) -> UserProfile:
    """
    Merge facts found in `text` into a profile.

    Values already present in `base` (for example filled in by the form) are
    never overwritten - explicit user input always wins.
    """
    profile = base.model_copy(deep=True) if base else UserProfile()
    if not text or not text.strip():
        return profile

    updates: dict = {
        "age": extract_age(text),
        "state": extract_state(text),
        "category": extract_category(text),
        "gender": extract_gender(text),
        "education_level": extract_education_level(text),
        "course": extract_course(text),
        "student_status": extract_student_status(text),
        "disability_status": extract_disability(text),
        "academic_percentage": extract_percentage(text),
        "family_income": parse_income(text),
    }

    for key, value in updates.items():
        if value is None:
            continue
        if getattr(profile, key, None) in (None, ""):
            setattr(profile, key, value)

    return profile


def extract_fields_found(text: str) -> list[str]:
    """Which profile fields could be read from the text (used for the trace)."""
    found = []
    checks = {
        "age": extract_age,
        "state": extract_state,
        "category": extract_category,
        "gender": extract_gender,
        "education_level": extract_education_level,
        "course": extract_course,
        "student_status": extract_student_status,
        "disability_status": extract_disability,
        "academic_percentage": extract_percentage,
    }
    for name, function in checks.items():
        try:
            if function(text):
                found.append(name)
        except Exception:  # pragma: no cover - defensive
            continue
    if parse_income(text):
        found.append("family_income")
    return found
