"""
Recommendation service: profile-driven, no free text needed.

Unlike /chat, this flow evaluates the **whole knowledge base** against the
profile (the rule engine is cheap and deterministic), then lets the LLM write
the explanation for the schemes that passed.
"""

from __future__ import annotations

from agents.graph import run_workflow
from agents.response_agent import schemes_for_display
from backend.config import settings
from models.api import RecommendedScheme, RecommendRequest, RecommendResponse
from models.scheme import Scheme
from utils.logging_utils import get_logger

logger = get_logger("services.recommend")

#: Criterion key -> friendly label for the UI.
CRITERION_LABELS = {
    "age": "age within range",
    "family_income": "family income within limit",
    "category": "category eligible",
    "state": "available in your state",
    "gender": "gender eligible",
    "education_level": "education level matches",
    "course": "course eligible",
    "student_status": "student status matches",
    "disability_status": "disability requirement met",
    "academic_percentage": "marks requirement met",
}


def _build_items(schemes: list[Scheme], state: dict) -> list[RecommendedScheme]:
    evaluations = {item.scheme_id: item for item in (state.get("evaluations") or [])}
    retrieval = {}
    for result in state.get("retrieval_results") or []:
        scheme_id = result.chunk.scheme_id
        retrieval[scheme_id] = max(retrieval.get(scheme_id, 0.0), result.score)

    items: list[RecommendedScheme] = []
    for scheme in schemes:
        evaluation = evaluations.get(scheme.scheme_id)
        if evaluation is None:
            continue
        items.append(
            RecommendedScheme(
                scheme=scheme.to_summary(),
                eligible=evaluation.is_eligible,
                score=evaluation.score,
                reason=evaluation.reason,
                checks=evaluation.checks,
                match_highlights=[
                    CRITERION_LABELS.get(criterion, criterion)
                    for criterion in evaluation.matched_criteria
                ],
                retrieval_score=round(retrieval.get(scheme.scheme_id, 0.0), 4),
            )
        )
    return items


def handle_recommend(request: RecommendRequest) -> RecommendResponse:
    state = run_workflow(
        question="",
        profile=request.profile,
        history=[],
        mode="recommend",
        top_n=request.top_n,
        scan_all=True,  # evaluate the whole knowledge base
    )

    eligible = _build_items(state.get("eligible") or [], state)
    near_misses = (
        _build_items(state.get("near_misses") or [], state)
        if request.include_near_misses
        else []
    )
    needs_more_info = _build_items(state.get("needs_more_info") or [], state)

    logger.info(
        "handle_recommend: %d eligible, %d near miss(es), %d need more info, provider=%s",
        len(eligible), len(near_misses), len(needs_more_info), state.get("llm_provider"),
    )

    return RecommendResponse(
        answer=state.get("answer", ""),
        eligible=eligible,
        near_misses=near_misses,
        needs_more_info=needs_more_info,
        missing_profile_fields=state.get("profile_missing", []),
        trace=[step.summary for step in (state.get("trace") or [])],
        llm_provider=state.get("llm_provider", "offline"),
        llm_used=bool(state.get("llm_used")),
        disclaimer=settings.data_disclaimer,
        citations=state.get("citations", []),
    )
