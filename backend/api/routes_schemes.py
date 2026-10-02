"""`/schemes` endpoints: browse, search and filter the knowledge base."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.config import settings
from models.api import SchemeListResponse
from models.scheme import SchemeSummary
from services.scheme_service import get_scheme, knowledge_base_stats, list_filters, list_schemes

router = APIRouter(tags=["schemes"])


@router.get("/schemes", response_model=SchemeListResponse, summary="Browse and search schemes")
def read_schemes(
    q: Optional[str] = Query(default=None, description="Free-text search, e.g. 'girls engineering'"),
    state: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None, description="General | OBC | EBC | SC | ST | DNT"),
    gender: Optional[str] = Query(default=None),
    education_level: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    scheme_type: Optional[str] = Query(default=None, description="scholarship | fellowship"),
    data_status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> SchemeListResponse:
    schemes = list_schemes(
        q=q,
        state=state,
        category=category,
        gender=gender,
        education_level=education_level,
        provider=provider,
        scheme_type=scheme_type,
        data_status=data_status,
        limit=limit,
    )
    stats = knowledge_base_stats()
    return SchemeListResponse(
        count=len(schemes),
        total_in_knowledge_base=stats["schemes"],
        disclaimer=settings.data_disclaimer,
        schemes=schemes,
    )


@router.get("/schemes/filters", summary="Filter options for the browse page")
def read_filters() -> dict:
    return {"disclaimer": settings.data_disclaimer, **list_filters()}


@router.get("/schemes/stats", summary="Knowledge base statistics")
def read_stats() -> dict:
    return {"disclaimer": settings.data_disclaimer, **knowledge_base_stats()}


@router.get("/schemes/{scheme_id}", response_model=SchemeSummary, summary="Get one scheme")
def read_scheme(scheme_id: str) -> SchemeSummary:
    scheme = get_scheme(scheme_id)
    if scheme is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scheme '{scheme_id}' was not found in the knowledge base.",
        )
    return scheme.to_summary()
