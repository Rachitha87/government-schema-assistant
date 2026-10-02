"""Scheme model: one record from the knowledge base."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Scheme(BaseModel):
    """
    A single scholarship / government scheme.

    The first block of fields is *human readable* (what the LLM and the UI
    show). The second block contains *structured filters* that the deterministic
    eligibility engine uses. Keeping both in one record means the assistant can
    never quote a benefit that the rule engine has not seen.
    """

    model_config = ConfigDict(populate_by_name=True)

    # --- Identity ---------------------------------------------------------
    scheme_id: str
    name: str
    provider: str = Field(description="Department / ministry that runs the scheme")

    # --- Human readable content (used by RAG + the UI) --------------------
    description: str
    eligibility: str = Field(description="Plain-language eligibility rules")
    income_limit: str = Field(default="Not specified", description="Income ceiling, in words")
    education_level: str = Field(default="Not specified")
    benefits: str = Field(description="What the applicant actually receives")
    deadline: str = Field(default="Check official portal")
    application_link: str = Field(default="", description="Official application URL")

    # --- Structured filters (used by the rule engine) --------------------
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    gender: str = "All"                     # All | Male | Female
    categories: list[str] = Field(default_factory=lambda: ["All"])
    max_annual_income: Optional[float] = None   # rupees per year
    states: list[str] = Field(default_factory=lambda: ["All"])
    education_levels: list[str] = Field(default_factory=lambda: ["Any"])
    course_keywords: list[str] = Field(default_factory=list)
    student_status: str = "Any"             # Any | Full-time | ...
    disability_required: bool = False
    min_percentage: Optional[float] = None

    # --- Provenance / safety ---------------------------------------------
    data_status: str = Field(
        default="sample-unverified",
        description="sample-unverified | officially-published",
    )
    notes: str = ""
    tags: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    @property
    def is_sample_data(self) -> bool:
        return self.data_status == "sample-unverified"

    def to_summary(self) -> "SchemeSummary":
        return SchemeSummary(
            scheme_id=self.scheme_id,
            name=self.name,
            provider=self.provider,
            description=self.description,
            eligibility=self.eligibility,
            income_limit=self.income_limit,
            education_level=self.education_level,
            benefits=self.benefits,
            deadline=self.deadline,
            application_link=self.application_link,
            data_status=self.data_status,
            tags=self.tags,
        )


class SchemeSummary(BaseModel):
    """Trimmed scheme payload for list endpoints and UI cards."""

    scheme_id: str
    name: str
    provider: str
    description: str
    eligibility: str
    income_limit: str
    education_level: str
    benefits: str
    deadline: str
    application_link: str
    data_status: str = "sample-unverified"
    tags: list[str] = Field(default_factory=list)


class RetrievalChunk(BaseModel):
    """One retrievable text block of a scheme (the unit of RAG)."""

    chunk_id: str
    scheme_id: str
    scheme_name: str
    provider: str
    section: str          # overview | eligibility | benefits | application
    text: str


class RetrievalResult(BaseModel):
    """A retrieved chunk plus its score(s)."""

    chunk: RetrievalChunk
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
