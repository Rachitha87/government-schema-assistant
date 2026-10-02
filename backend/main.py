"""
FastAPI application entry point.

Run from the project root:

    uvicorn backend.main:app --reload --port 8000

Then open http://127.0.0.1:8000/docs for the interactive API documentation.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.graph import get_graph
from backend.api.routes_chat import router as chat_router
from backend.api.routes_meta import router as meta_router
from backend.api.routes_recommend import router as recommend_router
from backend.api.routes_schemes import router as schemes_router
from backend.config import settings
from llm.factory import get_llm_client
from rag.loader import get_scheme_store
from rag.retriever import get_retriever
from utils.logging_utils import get_logger

logger = get_logger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the heavy objects once, at startup."""
    store = get_scheme_store()
    retriever = get_retriever()
    client = get_llm_client()
    get_graph()  # compile the LangGraph workflow

    logger.info("=" * 68)
    logger.info("%s v%s starting", settings.app_name, settings.app_version)
    logger.info("Knowledge base : %s (%d schemes)", settings.knowledge_base_path, len(store))
    logger.info("Retrieval      : %s", retriever.retrieval_mode)
    logger.info(
        "LLM provider   : %s (model=%s)",
        client.name,
        client.model,
    )
    if client.name == "offline":
        logger.info(
            "No LLM key found -> retrieval-only answers (still grounded, no API key needed). "
            "Set GROK_API_KEY in .env to switch to Grok."
        )
    logger.info("=" * 68)

    yield

    logger.info("%s stopped", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "RAG + agentic AI backend that helps users discover government scholarships "
        "and welfare schemes.\n\n"
        f"**{settings.data_disclaimer}**"
    ),
    lifespan=lifespan,
)

# The React dev server runs on a different port, so CORS is required.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router)
app.include_router(schemes_router)
app.include_router(recommend_router)
app.include_router(chat_router)


@app.get("/", tags=["meta"], summary="Service banner")
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": [
            "GET  /health",
            "GET  /meta",
            "GET  /schemes",
            "GET  /schemes/filters",
            "GET  /schemes/stats",
            "GET  /schemes/{scheme_id}",
            "POST /recommend",
            "POST /chat",
        ],
        "disclaimer": settings.data_disclaimer,
    }
