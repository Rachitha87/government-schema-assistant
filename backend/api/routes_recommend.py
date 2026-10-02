"""`/recommend` endpoint: profile-driven recommendations."""

from __future__ import annotations

from fastapi import APIRouter

from models.api import RecommendRequest, RecommendResponse
from services.recommendation_service import handle_recommend

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse, summary="Get recommendations for a profile")
def recommend(request: RecommendRequest) -> RecommendResponse:
    """
    Evaluates the whole knowledge base against the submitted profile with the
    deterministic rule engine, then lets the LLM explain the results.
    """
    return handle_recommend(request)
