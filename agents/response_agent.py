"""
Agent 5 - Response Agent.

Responsibilities
    * build the prompt: the retrieved scheme facts, the applicant profile and
      the user's question - nothing else,
    * ask the configured LLM to turn that into a helpful answer
      (or use the offline retrieval-only writer when no key is configured),
    * run the grounding check: any URL / amount / date that is not in the
      retrieved scheme text is flagged (and unknown links are removed),
    * return citations so the user can see exactly which schemes were used.
"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState, add_trace
from llm.factory import chat_with_fallback
from models.scheme import Scheme
from rag.loader import get_scheme_store
from rag.prompts import (
    build_chat_messages,
    build_insufficient_context_message,
    build_recommendation_messages,
)
from utils.grounding import check_grounding
from utils.logging_utils import get_logger
from utils.text_utils import truncate

logger = get_logger("agents.response")

AGENT_NAME = "Response Agent"


def _select_schemes(state: AgentState, top_n: int) -> list[Scheme]:
    """
    Which schemes may be discussed in the answer.

    Preference order:
      1. schemes the rule engine marked eligible (in ranked order),
      2. otherwise the best retrieved schemes, so the user still gets something
         useful even when the profile is incomplete.
    """
    ranked = state.get("ranking") or []
    eligible = state.get("eligible") or []
    by_id = {scheme.scheme_id: scheme for scheme in eligible}

    if eligible:
        selected = [by_id[scheme_id] for scheme_id in ranked if scheme_id in by_id]
        selected += [
            scheme for scheme in eligible if scheme.scheme_id not in {item.scheme_id for item in selected}
        ]
        return selected[:top_n]

    candidates = state.get("candidate_schemes") or []
    if state.get("mode") == "recommend":
        return (
            state.get("near_misses") or state.get("needs_more_info") or []
        )[:top_n]
    return candidates[:top_n]


def _build_notes(state: AgentState) -> dict[str, str]:
    notes: dict[str, str] = {}
    for evaluation in state.get("evaluations") or []:
        notes[evaluation.scheme_id] = evaluation.reason
    return notes


def run(state: AgentState) -> dict[str, Any]:
    store = get_scheme_store()
    top_n = max(int(state.get("top_n", 5)), 1)
    schemes = _select_schemes(state, top_n)
    notes = _build_notes(state)

    # ------------------------------------------------------------------
    # Nothing retrieved -> answer honestly, without calling the LLM.
    # ------------------------------------------------------------------
    if not schemes:
        answer = build_insufficient_context_message(
            state.get("question") or "your profile"
        )
        logger.info("%s: nothing retrieved, answering with the 'insufficient context' reply", AGENT_NAME)
        update: dict[str, Any] = {
            "answer": answer,
            "citations": [],
            "llm_provider": "none",
            "llm_used": False,
            "grounding_warnings": [],
        }
        update.update(
            add_trace(
                state,
                AGENT_NAME,
                "no matching scheme in the knowledge base; replied that the information "
                "is not available instead of guessing",
            )
        )
        return update

    # ------------------------------------------------------------------
    # Ask the LLM (or the offline writer) to phrase the answer.
    # ------------------------------------------------------------------
    if state.get("mode") == "recommend":
        messages = build_recommendation_messages(state.get("profile"), schemes, notes)
    else:
        messages = build_chat_messages(
            question=state.get("question") or "",
            schemes=schemes,
            profile=state.get("profile"),
            history=state.get("history"),
            notes=notes,
        )

    response = chat_with_fallback(messages)
    answer = response.text.strip()

    # ------------------------------------------------------------------
    # Guard-rails: is every claim backed by the retrieved text?
    # ------------------------------------------------------------------
    # The applicant's own income is a legitimate thing to quote back to them.
    profile = state.get("profile")
    extra_money = [profile.family_income] if profile and profile.family_income else []
    answer, warnings = check_grounding(answer, schemes, extra_allowed_money=extra_money)
    if warnings:
        logger.warning("%s: grounding warnings -> %s", AGENT_NAME, warnings)

    citations = [
        f"{scheme.scheme_id} - {scheme.name} ({scheme.provider})" for scheme in schemes
    ]

    # Be explicit when the answer is based on an incomplete profile, otherwise
    # "eligible" would look like a confirmed decision.
    missing = state.get("profile_missing") or []
    if missing and schemes:
        answer = (
            f"{answer}\n\n_Heads up: your profile is still missing "
            f"{', '.join(missing)}, so I could only check part of the eligibility rules. "
            "Treat the schemes above as candidates to verify, not confirmed eligibility._"
        )

    logger.info(
        "%s: answered with %s (model=%s, %d citation(s))",
        AGENT_NAME, response.provider, response.model, len(citations),
    )

    update = {
        "answer": answer,
        "citations": citations,
        "llm_provider": response.provider,
        "llm_used": response.used_llm,
        "llm_error": response.error,
        "grounding_warnings": warnings,
    }

    trace_summary = (
        f"wrote the answer with {response.provider} ({response.model}); "
        f"grounded in {len(schemes)} scheme(s)"
    )
    if response.error:
        trace_summary += f"; provider error, fell back to retrieval-only: {truncate(response.error, 120)}"
    if warnings:
        trace_summary += f"; {len(warnings)} grounding warning(s)"
    update.update(add_trace(state, AGENT_NAME, trace_summary))
    return update


def schemes_for_display(state: AgentState) -> list[Scheme]:
    """Helper used by the API layer to return the same schemes as the answer."""
    return _select_schemes(state, max(int(state.get("top_n", 5)), 1))
