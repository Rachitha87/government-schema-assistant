"""
Normalisation helpers.

Free text ("2 lakh", "obc", "class 11", "karnataka") has to be converted into
the canonical values used by the deterministic eligibility rules, otherwise the
rule engine would silently match nothing.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical values
# ---------------------------------------------------------------------------
CATEGORIES = ["General", "OBC", "EBC", "SC", "ST", "DNT"]

CATEGORY_SYNONYMS: dict[str, str] = {
    "general": "General",
    "gen": "General",
    "ur": "General",
    "obc": "OBC",
    "other backward class": "OBC",
    "other backward": "OBC",
    "bc": "OBC",
    "ebc": "EBC",
    "economically backward class": "EBC",
    "sebc": "EBC",
    "sc": "SC",
    "scheduled caste": "SC",
    "st": "ST",
    "scheduled tribe": "ST",
    "tribal": "ST",
    "dnt": "DNT",
    "deemed to have been": "DNT",
}

GENDERS = ["Male", "Female", "Other"]

GENDER_SYNONYMS: dict[str, str] = {
    "male": "Male",
    "m": "Male",
    "boy": "Male",
    "man": "Male",
    "female": "Female",
    "f": "Female",
    "woman": "Female",
    "girl": "Female",
    "women": "Female",
    "other": "Other",
    "non binary": "Other",
    "third": "Other",
}

STUDENT_STATUSES = ["Full-time", "Part-time", "Job/Working", "Unemployed"]

STUDENT_STATUS_SYNONYMS: dict[str, str] = {
    "full time": "Full-time",
    "fulltime": "Full-time",
    "school student": "Full-time",
    "college student": "Full-time",
    "part time": "Part-time",
    "parttime": "Part-time",
    "working": "Job/Working",
    "employed": "Job/Working",
    "job": "Job/Working",
    "salaried": "Job/Working",
    "part time job": "Job/Working",
    "unemployed": "Unemployed",
    "looking for job": "Unemployed",
}

DISABILITY_VALUES: dict[str, str] = {
    "yes": "Yes",
    "y": "Yes",
    "true": "Yes",
    "disabled": "Yes",
    "no": "No",
    "n": "No",
    "false": "No",
    "not disabled": "No",
    "prefer not to say": "Prefer not to say",
    "": "Prefer not to say",
    "none": "Prefer not to say",
}

# Canonical education levels, ordered from lowest to highest.
EDUCATION_LEVELS = [
    "School (Class 1-8)",
    "Class 9-12",
    "Class 11 and above",
    "Diploma",
    "Undergraduate",
    "Postgraduate",
    "MPhil/PhD",
]

# Levels that stay open-ended, i.e. "Class 11 and above" also covers a
# university student who has already cleared class 12.
OPEN_ENDED_LEVELS = {"Class 11 and above"}

EDUCATION_SYNONYMS: dict[str, str] = {
    "class 1-8": "School (Class 1-8)",
    "class 8": "School (Class 1-8)",
    "class 1 to 8": "School (Class 1-8)",
    "primary": "School (Class 1-8)",
    "middle school": "School (Class 1-8)",
    "class 9-12": "Class 9-12",
    "class 9": "Class 9-12",
    "class 10": "Class 9-12",
    "class 10th": "Class 9-12",
    "class 9th": "Class 9-12",
    "class 11": "Class 9-12",
    "class 12": "Class 9-12",
    "class 11th": "Class 9-12",
    "class 12th": "Class 9-12",
    "10th": "Class 9-12",
    "12th": "Class 9-12",
    "intermediate": "Class 9-12",
    "higher secondary": "Class 9-12",
    "secondary": "Class 9-12",
    "high school": "Class 9-12",
    "school": "Class 9-12",
    "11 and above": "Class 11 and above",
    "class 11 and above": "Class 11 and above",
    "post matric": "Class 11 and above",
    "post matriculation": "Class 11 and above",
    "class 11 or above": "Class 11 and above",
    "diploma": "Diploma",
    "polytechnic": "Diploma",
    "iti": "Diploma",
    "undergraduate": "Undergraduate",
    "under graduation": "Undergraduate",
    "ug": "Undergraduate",
    "graduation": "Undergraduate",
    "bachelor": "Undergraduate",
    "bca": "Undergraduate",
    "btech": "Undergraduate",
    "be": "Undergraduate",
    "bsc": "Undergraduate",
    "bcom": "Undergraduate",
    "ba": "Undergraduate",
    "bba": "Undergraduate",
    "bpharm": "Undergraduate",
    "btech": "Undergraduate",
    "engineering": "Undergraduate",
    "postgraduate": "Postgraduate",
    "post graduate": "Postgraduate",
    "postgraduation": "Postgraduate",
    "pg": "Postgraduate",
    "master": "Postgraduate",
    "masters": "Postgraduate",
    "mca": "Postgraduate",
    "msc": "Postgraduate",
    "mtech": "Postgraduate",
    "mba": "Postgraduate",
    "ma": "Postgraduate",
    "mcom": "Postgraduate",
    "mphil": "MPhil/PhD",
    "phd": "MPhil/PhD",
    "doctorate": "MPhil/PhD",
    "doctoral": "MPhil/PhD",
}

# Indian states / union territories, canonical spelling.
INDIAN_STATES: list[str] = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry", "Ladakh",
]

_STATE_LOOKUP: dict[str, str] = {}
for _state in INDIAN_STATES:
    _STATE_LOOKUP[_state.lower()] = _state
    _STATE_LOOKUP[_state.lower().replace(" ", "")] = _state
    _STATE_LOOKUP[_state.lower().split()[0]] = _state


# ---------------------------------------------------------------------------
# Generic normalisers
# ---------------------------------------------------------------------------
def _lookup(value: Optional[str], table: dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip().lower())
    if not text:
        return None
    if text in table:
        return table[text]
    # Fall back to a "contains" match, e.g. "female" in "female candidates".
    for key, mapped in table.items():
        if len(key) > 3 and key in text:
            return mapped
    return None


def normalise_category(value: Optional[str]) -> Optional[str]:
    return _lookup(value, CATEGORY_SYNONYMS)


def normalise_gender(value: Optional[str]) -> Optional[str]:
    return _lookup(value, GENDER_SYNONYMS)


def normalise_student_status(value: Optional[str]) -> Optional[str]:
    return _lookup(value, STUDENT_STATUS_SYNONYMS)


def normalise_disability_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    for key, mapped in DISABILITY_VALUES.items():
        if key and key in text:
            return mapped
    return None


def normalise_state(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    key = text.lower()
    if key in _STATE_LOOKUP:
        return _STATE_LOOKUP[key]
    compact = key.replace(" ", "")
    if compact in _STATE_LOOKUP:
        return _STATE_LOOKUP[compact]
    first_word = key.split()[0]
    if first_word in _STATE_LOOKUP:
        return _STATE_LOOKUP[first_word]
    # Unknown text: return it as-is so it can still be shown in the UI.
    return text.title()


def normalise_education_level(value: Optional[str]) -> Optional[str]:
    return _lookup(value, EDUCATION_SYNONYMS)


def education_rank(level: Optional[str]) -> Optional[int]:
    if level is None:
        return None
    try:
        return EDUCATION_LEVELS.index(level)
    except ValueError:
        return None


def education_matches(profile_level: Optional[str], scheme_levels: list[str]) -> bool:
    """
    Does the applicant's stage of education satisfy a scheme's requirement?

    Rules (simple on purpose, so behaviour is predictable):
      * "Any" always matches.
      * An exact match always matches.
      * A scheme level flagged as open-ended ("Class 11 and above") also matches
        any *higher* stage.
      * Anything else is not a match.
    """
    if not scheme_levels or any(str(item).lower() == "any" for item in scheme_levels):
        return True
    if profile_level is None:
        return True  # cannot check -> do not block the user
    if profile_level in scheme_levels:
        return True
    profile_rank = education_rank(profile_level)
    for level in scheme_levels:
        if level in OPEN_ENDED_LEVELS:
            scheme_rank = education_rank(level)
            if profile_rank is not None and scheme_rank is not None and profile_rank >= scheme_rank:
                return True
    return False


# ---------------------------------------------------------------------------
# Number parsing (used when reading a chat message)
# ---------------------------------------------------------------------------
_UNITS = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000,
          "crore": 10_000_000, "crores": 10_000_000}

_UNIT_RE = re.compile(
    r"([0-9][0-9,._]*)\s*(crore|crores|lakh|lakhs)\b", re.IGNORECASE
)
_CURRENCY_RE = re.compile(
    r"(?:rs\.?|inr|₹)\s*([0-9][0-9,._]*)\s*(crore|crores|lakh|lakhs)?",
    re.IGNORECASE,
)
# "family income is 2 lakh", "annual income of 2,50,000"
_INCOME_KEYWORD_RE = re.compile(
    r"(?:income|salary|family\s+income|annual\s+income|total\s+income)[^0-9]{0,30}"
    r"([0-9][0-9,._]*)\s*(crore|crores|lakh|lakhs|thousand|hundred)?",
    re.IGNORECASE,
)


def _to_rupees(amount: str, unit: str | None, assume_lakhs: bool = False) -> Optional[float]:
    raw = str(amount).replace(",", "").replace("_", "").rstrip(".")
    try:
        value = float(raw)
    except ValueError:
        return None
    if unit:
        return value * _UNITS.get(unit.lower(), 1)
    # No unit: a small number next to the word "income" is meant as lakhs
    # ("family income is 2.5"), otherwise it is already rupees.
    if assume_lakhs and 0 < value < 1000:
        return value * 100_000
    return value


def parse_income(text: Optional[str]) -> Optional[float]:
    """
    Convert a free-text income into rupees per year.

    Patterns are tried from the most explicit to the least explicit, so a bare
    number that is not next to an income keyword is never guessed at.

    Examples:
        "2 lakh"                  -> 200000.0
        "Rs. 2,50,000 / year"     -> 250000.0
        "family income is 2 lakh" -> 200000.0
        "1.5 lakhs per annum"     -> 150000.0
        "3 crore"                 -> 30000000.0
    """
    if not text:
        return None

    text = str(text)

    # 1. An explicit unit is always the strongest signal.
    match = _UNIT_RE.search(text)
    if match:
        return _to_rupees(match.group(1), match.group(2))

    # 2. An explicit currency symbol / "Rs." prefix.
    match = _CURRENCY_RE.search(text)
    if match:
        return _to_rupees(match.group(1), match.group(2) if match.lastindex and match.lastindex >= 2 else None)

    # 3. A number next to an income keyword.
    match = _INCOME_KEYWORD_RE.search(text)
    if match:
        unit = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        return _to_rupees(match.group(1), unit, assume_lakhs=True)

    return None


def format_income(value: Optional[float]) -> str:
    """Rupees -> "Rs. 2.5 lakh" style text for prompts and labels."""
    if value is None:
        return "not provided"
    if value >= 10_000_000:
        return f"Rs. {value / 10_000_000:.2f} crore"
    if value >= 100_000:
        return f"Rs. {value / 100_000:.1f} lakh"
    return f"Rs. {value:,.0f}"
