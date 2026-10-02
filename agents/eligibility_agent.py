"""
Agent 3 - Eligibility Checking Agent.

Responsibilities
    * run the deterministic rule engine (utils/eligibility.py) for every
      candidate scheme,
    * separate "eligible", "not eligible" and "not enough information",
    * attach a human-readable reason and a per-criterion breakdown to each
      result so the answer can explain *why*.

This agent never calls an LLM. Eligibility must be reproducible.
"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState, add_trace
from utils.eligibility import INSUFFICIENT, evaluate_all, summarise
from utils.logging_utils import get_logger

logger = get_logger("agents.eligibility")

AGENT_NAME = "Eligibility Checking Agent"


def run(state: AgentState) -> dict[str, Any]:
    schemes = state.get("candidate_schemes") or []
    profile = state.get("profile")

    if not schemes:
        logger.info("%s: no candidate schemes to evaluate", AGENT_NAME)
        update: dict[str, Any] = {"evaluations": []}
        update.update(add_trace(state, AGENT_NAME, "no candidate schemes to evaluate"))
        return update

    evaluations = evaluate_all(schemes, profile)
    counts = summarise(evaluations)
    logger.info("%s: %s", AGENT_NAME, counts)

    missing = state.get("profile_missing") or profile.missing_fields()
    note = (
        f" (profile incomplete, so {counts['insufficient_data']} scheme(s) could not be fully "
        f"verified - missing: {', '.join(missing)})"
        if counts["insufficient_data"] and missing
        else ""
    )

    update = {"evaluations": evaluations}
    update.update(
        add_trace(
            state,
            AGENT_NAME,
            f"checked {counts['evaluated']} scheme(s): {counts['eligible']} eligible, "
            f"{counts['not_eligible']} not eligible, "
            f"{counts['insufficient_data']} need more details{note}",
        )
    )
    return update
