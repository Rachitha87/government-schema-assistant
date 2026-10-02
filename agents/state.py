"""
Shared state for the LangGraph workflow.

A LangGraph workflow is a set of functions (nodes) that receive this state and
return a *partial* update of it. Keeping every key in one typed dictionary
makes the whole pipeline easy to follow - and easy to print while debugging.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from models.api import AgentTraceStep, ChatMessage
from models.profile import UserProfile
from models.scheme import RetrievalResult, Scheme
from utils.eligibility import EvaluationResult


class AgentState(TypedDict, total=False):
    """Everything the agents read and write. Every key is optional."""

    # --- inputs -----------------------------------------------------------
    question: str                 # the user's message (empty for /recommend)
    profile: UserProfile          # profile from the form, if any
    history: list[ChatMessage]    # previous chat turns
    mode: str                     # "chat" or "recommend"
    top_n: int                    # how many schemes to return
    scan_all: bool                # evaluate the whole KB, not just retrieved

    # --- intermediate values ----------------------------------------------
    extracted_fields: list[str]
    profile_missing: list[str]
    retrieval_results: list[RetrievalResult]
    candidate_schemes: list[Scheme]
    evaluations: list[EvaluationResult]

    # --- outputs ----------------------------------------------------------
    eligible: list[Scheme]
    near_misses: list[Scheme]
    needs_more_info: list[Scheme]
    answer: str
    citations: list[str]
    trace: list[AgentTraceStep]
    llm_provider: str
    llm_used: bool
    llm_error: Optional[str]
    grounding_warnings: list[str]
    retrieval_debug: list[dict[str, Any]]


def new_state(
    question: str = "",
    profile: Optional[UserProfile] = None,
    history: Optional[list[ChatMessage]] = None,
    mode: str = "chat",
    top_n: int = 5,
    scan_all: bool = False,
) -> AgentState:
    """Build a fresh state dictionary with every key present."""
    return AgentState(
        question=question,
        profile=profile or UserProfile(),
        history=history or [],
        mode=mode,
        top_n=top_n,
        scan_all=scan_all,
        extracted_fields=[],
        profile_missing=[],
        retrieval_results=[],
        candidate_schemes=[],
        evaluations=[],
        eligible=[],
        near_misses=[],
        needs_more_info=[],
        answer="",
        citations=[],
        trace=[],
        llm_provider="offline",
        llm_used=False,
        llm_error=None,
        grounding_warnings=[],
        retrieval_debug=[],
    )


def add_trace(state: AgentState, agent: str, summary: str) -> dict[str, Any]:
    """Helper that returns a partial state update containing one trace step."""
    trace = list(state.get("trace") or [])
    trace.append(AgentTraceStep(agent=agent, summary=summary))
    return {"trace": trace}
