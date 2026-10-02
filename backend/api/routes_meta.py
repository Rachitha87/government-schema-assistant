"""`/health` and `/meta` endpoints used by the frontend to show system status."""

from __future__ import annotations

from fastapi import APIRouter

from agents.graph import graph_summary
from backend.config import settings
from llm.factory import get_llm_client
from models.api import HealthResponse
from services.scheme_service import knowledge_base_stats

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse, summary="System status")
def health() -> HealthResponse:
    client = get_llm_client()
    stats = knowledge_base_stats()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        llm_provider=client.name,
        llm_available=client.name != "offline",
        schemes_loaded=stats["schemes"],
        knowledge_base_file=stats["file"],
        retrieval=stats["retrieval"],
        disclaimer=settings.data_disclaimer,
    )


@router.get("/meta", summary="App metadata for the frontend")
def meta() -> dict:
    """Everything the UI needs on boot: filters, agent graph, disclaimer."""
    client = get_llm_client()
    stats = knowledge_base_stats()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "llm": {
            "provider": client.name,
            "model": client.model,
            "available": client.available,
            "llm_enabled": client.name != "offline",
            "hint": (
                "Add GROK_API_KEY to your backend .env file to enable AI-written answers."
                if client.name == "offline"
                else "Answers are written by the configured LLM and checked against the knowledge base."
            ),
        },
        "knowledge_base": stats,
        "agents": graph_summary(),
        "disclaimer": settings.data_disclaimer,
    }
