"""
Agent 1 - User Profile Agent.

Responsibilities
    * merge the profile submitted by the form with facts found in the message
      ("I am 21, from Karnataka, family income 2 lakh"),
    * normalise those facts (income -> rupees, "obc" -> "OBC"),
    * report which fields are still missing so the response can ask for them.

It uses deterministic rules, not an LLM - see utils/profile_extractor.py.
"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState, add_trace
from utils.logging_utils import get_logger
from utils.profile_extractor import extract_fields_found, parse_profile_from_text
from utils.text_utils import truncate

logger = get_logger("agents.profile")

AGENT_NAME = "User Profile Agent"


def run(state: AgentState) -> dict[str, Any]:
    question = state.get("question") or ""
    profile = state.get("profile")

    fields_found = extract_fields_found(question) if question else []
    merged = parse_profile_from_text(question, base=profile) if question else profile

    missing = merged.missing_fields()
    logger.info("%s: profile=%s | missing=%s", AGENT_NAME, merged.summary(), missing or "none")

    update: dict[str, Any] = {
        "profile": merged,
        "extracted_fields": fields_found,
        "profile_missing": missing,
    }
    update.update(
        add_trace(
            state,
            AGENT_NAME,
            f"read {len(fields_found)} field(s) from the message ({', '.join(fields_found) or 'none'})"
            f"; profile: {truncate(merged.summary(), 120)}"
            + (f"; still missing: {', '.join(missing)}" if missing else ""),
        )
    )
    return update
