"""
Deterministic eligibility filtering.
IMPORTANT: This module never calls an LLM. Eligibility must be exact,
reproducible rule matching -- not a language model's guess.
"""

from pydantic import BaseModel
from typing import Optional


class UserProfile(BaseModel):
    age: Optional[int] = None
    category: Optional[str] = None          # General / OBC / SC / ST
    annual_income: Optional[int] = None      # in rupees
    state: Optional[str] = None
    education_level: Optional[str] = None    # e.g. "Class 9-12", "Undergraduate"
    gender: Optional[str] = None


REQUIRED_FIELDS = ["age", "category", "annual_income", "state", "education_level"]


def missing_fields(profile: UserProfile) -> list[str]:
    """Fields still needed before we can reliably filter eligibility."""
    return [f for f in REQUIRED_FIELDS if getattr(profile, f) is None]


def check_eligibility(scheme: dict, profile: UserProfile) -> tuple[bool, str]:
    """
    Returns (is_eligible, reason).
    `scheme` is expected to be a dict matching the schemes.csv columns.
    Only checks fields that are present in both the scheme and the profile --
    unknown scheme fields (blank in the CSV) are treated as "no restriction".
    """
    reasons = []

    if profile.age is not None and scheme.get("min_age") not in (None, ""):
        if not (int(scheme["min_age"]) <= profile.age <= int(scheme.get("max_age", 200))):
            return False, f"Age {profile.age} is outside the eligible range " \
                           f"({scheme['min_age']}-{scheme.get('max_age', '?')})"

    if profile.annual_income is not None and scheme.get("max_income") not in (None, ""):
        if profile.annual_income > int(scheme["max_income"]):
            return False, f"Family income exceeds the ceiling of ₹{scheme['max_income']}"

    if profile.category and scheme.get("categories") not in (None, "", "All"):
        allowed = [c.strip() for c in str(scheme["categories"]).split(",")]
        if profile.category not in allowed:
            return False, f"Category '{profile.category}' not in eligible categories {allowed}"

    if profile.state and scheme.get("states") not in (None, "", "All"):
        allowed_states = [s.strip() for s in str(scheme["states"]).split(",")]
        if profile.state not in allowed_states:
            return False, f"Scheme is restricted to {allowed_states}, not available in {profile.state}"

    if profile.gender and scheme.get("gender") not in (None, "", "All"):
        if profile.gender != scheme["gender"]:
            return False, f"Scheme is restricted to {scheme['gender']} applicants"

    reasons.append("Meets all known eligibility criteria")
    return True, "; ".join(reasons)


if __name__ == "__main__":
    # Quick manual test -- run `python src/eligibility.py` to sanity check
    sample_scheme = {
        "min_age": 13, "max_age": 20, "categories": "OBC",
        "max_income": 250000, "states": "All", "gender": "All"
    }
    profile = UserProfile(age=17, category="OBC", annual_income=200000, state="Karnataka")
    print(check_eligibility(sample_scheme, profile))

    profile_too_rich = UserProfile(age=17, category="OBC", annual_income=500000, state="Karnataka")
    print(check_eligibility(sample_scheme, profile_too_rich))