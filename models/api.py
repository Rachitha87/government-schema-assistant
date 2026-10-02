"""Request / response models for the HTTP API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from models.profile import UserProfile
from models.scheme import SchemeSummary


# ---------------------------------------------------------------------------
# /schemes
# ---------------------------------------------------------------------------
class SchemeListResponse(BaseModel):
    count: int
    total_in_knowledge_base: int
    disclaimer: str
    schemes: list[SchemeSummary]


# ---------------------------------------------------------------------------
# /recommend
# ---------------------------------------------------------------------------
class RecommendRequest(BaseModel):
    profile: UserProfile
    top_n: int = Field(default=6, ge=1, le=25)
    include_near_misses: bool = Field(
        default=True,
        description="Also return schemes the user is *almost* eligible for.",
    )


class EligibilityCheck(BaseModel):
    """Per-criterion result of the deterministic rule engine."""

    criterion: str
    passed: Optional[bool] = None   # None => could not be checked
    detail: str
    hard: bool = Field(
        default=True,
        description=(
            "A hard check is a mandatory rule (category, state, gender, age, "
            "income). If it cannot be verified the scheme is not confirmed as "
            "eligible. Soft checks (e.g. marks) only affect the reason text."
        ),
    )


class RecommendedScheme(BaseModel):
    scheme: SchemeSummary
    eligible: bool
    score: float
    reason: str
    checks: list[EligibilityCheck] = Field(default_factory=list)
    match_highlights: list[str] = Field(default_factory=list)
    retrieval_score: float = 0.0


class RecommendResponse(BaseModel):
    answer: str
    eligible: list[RecommendedScheme] = Field(default_factory=list)
    near_misses: list[RecommendedScheme] = Field(default_factory=list)
    needs_more_info: list[RecommendedScheme] = Field(
        default_factory=list,
        description="Schemes that match partially but need a missing profile field.",
    )
    missing_profile_fields: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    llm_provider: str = "offline"
    llm_used: bool = False
    disclaimer: str
    citations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="The user's question")
    profile: Optional[UserProfile] = None
    history: list[ChatMessage] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=15)


class AgentTraceStep(BaseModel):
    agent: str
    summary: str


class ChatResponse(BaseModel):
    answer: str
    matched_schemes: list[SchemeSummary] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    profile_used: dict = Field(default_factory=dict)
    missing_profile_fields: list[str] = Field(default_factory=list)
    trace: list[AgentTraceStep] = Field(default_factory=list)
    llm_provider: str = "offline"
    llm_used: bool = False
    grounded: bool = True
    grounding_warnings: list[str] = Field(default_factory=list)
    disclaimer: str
    retrieval_debug: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    llm_provider: str
    llm_available: bool
    schemes_loaded: int
    knowledge_base_file: str
    retrieval: dict
    disclaimer: str
