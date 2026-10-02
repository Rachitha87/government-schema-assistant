"""
Chat service: runs the multi-agent workflow for a user's question and shapes
the result into the API response.
"""

from __future__ import annotations

from agents.graph import run_workflow
from agents.response_agent import schemes_for_display
from models.api import AgentTraceStep, ChatRequest, ChatResponse
from models.scheme import SchemeSummary
from backend.config import settings
from utils.logging_utils import get_logger

logger = get_logger("services.chat")


def handle_chat(request: ChatRequest) -> ChatResponse:
    state = run_workflow(
        question=request.message,
        profile=request.profile,
        history=request.history,
        mode="chat",
        top_n=request.top_n,
        scan_all=False,
    )

    schemes = schemes_for_display(state)
    trace = state.get("trace") or []

    logger.info(
        "handle_chat: provider=%s used_llm=%s schemes=%d",
        state.get("llm_provider"), state.get("llm_used"), len(schemes),
    )

    return ChatResponse(
        answer=state.get("answer", ""),
        matched_schemes=[scheme.to_summary() for scheme in schemes],
        citations=state.get("citations", []),
        profile_used=state.get("profile").to_dict() if state.get("profile") else {},
        missing_profile_fields=state.get("profile_missing", []),
        trace=[AgentTraceStep(**step.model_dump()) if hasattr(step, "model_dump") else step for step in trace],
        llm_provider=state.get("llm_provider", "offline"),
        llm_used=bool(state.get("llm_used")),
        grounded=not state.get("grounding_warnings"),
        grounding_warnings=state.get("grounding_warnings", []),
        disclaimer=settings.data_disclaimer,
        retrieval_debug=state.get("retrieval_debug", []),
    )
