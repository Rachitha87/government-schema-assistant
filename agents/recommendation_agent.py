"""
Agent 4 - Recommendation Agent.

Responsibilities
    * rank the eligible schemes, using
        - the rule-engine score (how many criteria were satisfied),
        - the retrieval score (how well the scheme matches the question),
        - a small bonus for schemes whose tags match the profile,
    * keep a short "almost eligible" list so the user knows what would unlock it,
    * never invent a scheme that the retrieval agent did not find.
"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState, add_trace
from models.scheme import Scheme
from utils.logging_utils import get_logger
from utils.text_utils import truncate

logger = get_logger("agents.recommendation")

AGENT_NAME = "Recommendation Agent"

#: How many "almost eligible" schemes to return at most.
MAX_NEAR_MISSES = 4


def _retrieval_scores(state: AgentState) -> dict[str, float]:
    scores: dict[str, float] = {}
    for result in state.get("retrieval_results") or []:
        scheme_id = result.chunk.scheme_id
        scores[scheme_id] = max(scores.get(scheme_id, 0.0), result.score)
    return scores


def _tag_bonus(scheme: Scheme, profile) -> float:
    """Small boost when the scheme's tags match words from the profile."""
    if not scheme.tags or profile is None:
        return 0.0
    haystack = " ".join(
        str(value).lower()
        for value in (
            profile.education_level, profile.course, profile.category,
            profile.state, profile.gender, profile.student_status,
        )
        if value
    )
    hits = sum(1 for tag in scheme.tags if tag and tag.lower() in haystack)
    return min(hits, 3) * 0.05


def run(state: AgentState) -> dict[str, Any]:
    evaluations = state.get("evaluations") or []
    schemes = {scheme.scheme_id: scheme for scheme in state.get("candidate_schemes") or []}
    profile = state.get("profile")
    top_n = max(int(state.get("top_n", 5)), 1)
    retrieval = _retrieval_scores(state)

    ranked: list[tuple[float, str]] = []
    near_misses: list[tuple[float, str]] = []
    unconfirmed: list[tuple[float, str]] = []

    for evaluation in evaluations:
        scheme = schemes.get(evaluation.scheme_id)
        if scheme is None:
            continue
        combined = (
            0.6 * evaluation.score
            + 0.3 * retrieval.get(evaluation.scheme_id, 0.0)
            + _tag_bonus(scheme, profile)
        )
        if evaluation.is_eligible:
            ranked.append((combined, scheme.scheme_id))
        elif evaluation.is_near_miss:
            near_misses.append((combined, scheme.scheme_id))
        elif evaluation.needs_more_info:
            unconfirmed.append((combined, scheme.scheme_id))

    ranked.sort(reverse=True)
    near_misses.sort(reverse=True)
    unconfirmed.sort(reverse=True)

    eligible = [schemes[scheme_id] for _, scheme_id in ranked[:top_n]]
    almost = [schemes[scheme_id] for _, scheme_id in near_misses[:MAX_NEAR_MISSES]]
    todo = [schemes[scheme_id] for _, scheme_id in unconfirmed[:MAX_NEAR_MISSES]]

    logger.info(
        "%s: %d eligible, %d near miss(es), %d need more info",
        AGENT_NAME, len(eligible), len(almost), len(todo),
    )

    update: dict[str, Any] = {
        "eligible": eligible,
        "near_misses": almost,
        "needs_more_info": todo,
        "retrieval_debug": list(state.get("retrieval_debug") or []),
    }
    update["ranking"] = [scheme_id for _, scheme_id in ranked[:top_n]]  # type: ignore[typeddict-unknown-key]

    summary = f"ranked {len(eligible)} eligible scheme(s)"
    if eligible:
        summary += f"; best match: {truncate(eligible[0].name, 60)}"
    if almost:
        summary += f"; {len(almost)} almost-eligible scheme(s) kept for reference"
    if todo:
        summary += f"; {len(todo)} scheme(s) need a missing profile field"
    update.update(add_trace(state, AGENT_NAME, summary))
    return update
