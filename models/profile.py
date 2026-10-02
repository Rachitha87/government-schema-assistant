"""
The user profile model.

The same object is used for:
  * the profile form in the frontend,
  * `POST /recommend`,
  * optional `POST /chat` context,
  * the deterministic eligibility rule engine.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileField(BaseModel):
    """A single field of the profile form, used to build it dynamically."""

    name: str
    label: str
    type: str = "text"
    required: bool = False
    options: list[str] = Field(default_factory=list)
    placeholder: str = ""
    help_text: str = ""


class UserProfile(BaseModel):
    """
    Everything the eligibility engine needs to know about the applicant.

    All fields are optional: a user may chat before filling the form, and the
    Profile Agent merges whatever it can find from the conversation.
    """

    model_config = ConfigDict(populate_by_name=True)

    # --- Identity ---------------------------------------------------------
    name: Optional[str] = Field(default=None, description="Applicant's full name")

    # --- Demographics -----------------------------------------------------
    age: Optional[int] = Field(default=None, ge=5, le=100)
    gender: Optional[str] = Field(default=None, description="Male | Female | Other")
    state: Optional[str] = Field(default=None, description="State / UT of residence")

    # --- Social / economic ------------------------------------------------
    category: Optional[str] = Field(
        default=None, description="General | OBC | EBC | SC | ST | DNT"
    )
    family_income: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total annual family income in rupees (not lakhs)",
    )

    # --- Academic ---------------------------------------------------------
    education_level: Optional[str] = Field(
        default=None,
        description="e.g. Class 9-12, Undergraduate, Postgraduate",
    )
    course: Optional[str] = Field(
        default=None, description="e.g. BCA, MCA, B.Tech, MA, M.Sc"
    )
    student_status: Optional[str] = Field(
        default=None,
        description="Full-time | Part-time | Job/Working | Unemployed",
    )

    # --- Disability (optional) -------------------------------------------
    disability_status: Optional[str] = Field(
        default=None, description="Yes | No | Prefer not to say"
    )
    disability_type: Optional[str] = Field(
        default=None, description="e.g. Locomotor, Visual, Hearing"
    )

    # --- Extras used by a few merit-based schemes ------------------------
    academic_percentage: Optional[float] = Field(
        default=None, ge=0, le=100, description="Last exam percentage"
    )

    # ------------------------------------------------------------------
    # Validators: normalise free text so the rule engine can compare values
    # ------------------------------------------------------------------
    @field_validator("gender", "disability_status", "student_status", mode="before")
    @classmethod
    def _normalise_choice(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("category", "state", "education_level", mode="before")
    @classmethod
    def _strip_text(cls, value):
        if value is None:
            return None
        text = " ".join(str(value).split())
        return text or None

    # ------------------------------------------------------------------
    # Convenience helpers used by agents / eligibility engine
    # ------------------------------------------------------------------
    @property
    def is_complete(self) -> bool:
        """True when every field needed for a reliable eligibility check exists."""
        required = (self.age, self.category, self.family_income, self.state, self.education_level)
        return all(value is not None for value in required)

    def missing_fields(self) -> list[str]:
        """Human readable list of fields still missing."""
        labels = {
            "age": "age",
            "category": "category",
            "family_income": "family income",
            "state": "state",
            "education_level": "education level",
        }
        missing = []
        for field_name, label in labels.items():
            if getattr(self, field_name) is None:
                missing.append(label)
        return missing

    def has_disability(self) -> bool:
        return str(self.disability_status or "").strip().lower() in {"yes", "true", "y"}

    def summary(self) -> str:
        """One-line profile summary used in prompts and logs."""
        parts = []
        if self.age:
            parts.append(f"{self.age} years old")
        if self.gender:
            parts.append(self.gender.lower())
        if self.state:
            parts.append(f"from {self.state}")
        if self.category:
            parts.append(f"category {self.category}")
        if self.family_income is not None:
            parts.append(f"family income Rs.{self.family_income:,.0f} per year")
        if self.education_level:
            parts.append(f"studying {self.education_level}")
        if self.course:
            parts.append(f"course {self.course}")
        if self.student_status:
            parts.append(self.student_status.lower())
        if self.has_disability():
            parts.append("person with disability")
        return ", ".join(parts) if parts else "no profile details provided"

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)
