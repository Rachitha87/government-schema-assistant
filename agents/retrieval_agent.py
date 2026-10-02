"""
Agent 2 - Scheme Retrieval Agent (the "R" in RAG).

Responsibilities
    * run a hybrid search (BM25 + optional embeddings) over the knowledge base,
    * use both the user's question and their profile as the query so that a vague
      question like "what can I apply for?" still returns personalised results,
    * hand a de-duplicated, ordered list of candidate schemes to the next agent,
    * keep a debug trail of the chunks that were retrieved (shown in the UI).
"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState, add_trace
from models.scheme import Scheme
from rag.retriever import get_retriever
from rag.loader import get_scheme_store
from utils.logging_utils import get_logger
from utils.text_utils import truncate

logger = get_logger("agents.retrieval")

AGENT_NAME = "Scheme Retrieval Agent"


def run(state: AgentState) -> dict[str, Any]:
    retriever = get_retriever()
    store = get_scheme_store()
    profile = state.get("profile")
    question = state.get("question") or ""

    results = retriever.retrieve_for_profile(
        profile, question=question, top_k=max(state.get("top_n", 5) * 3, 12)
    )

    # Keep the best-scoring scheme, plus any extra schemes the rule engine
    # should still look at when we are recommending (scan_all).
    ordered: list[Scheme] = []
    seen: set[str] = set()
    for result in results:
        scheme = store.get(result.chunk.scheme_id)
        if scheme and scheme.scheme_id not in seen:
            seen.add(scheme.scheme_id)
            ordered.append(scheme)

    if state.get("scan_all"):
        # Recommendation flow: evaluate the entire knowledge base, then rank.
        for scheme in store.all():
            if scheme.scheme_id not in seen:
                seen.add(scheme.scheme_id)
                ordered.append(scheme)

    debug = [
        {
            "scheme_id": result.chunk.scheme_id,
            "scheme_name": result.chunk.scheme_name,
            "section": result.chunk.section,
            "score": result.score,
            "lexical_score": result.lexical_score,
            "semantic_score": result.semantic_score,
        }
        for result in results
    ]

    logger.info(
        "%s: %d chunk(s) -> %d candidate scheme(s) [%s]",
        AGENT_NAME, len(results), len(ordered), retriever.retrieval_mode,
    )

    update: dict[str, Any] = {
        "retrieval_results": results,
        "candidate_schemes": ordered,
        "retrieval_debug": debug,
    }
    update.update(
        add_trace(
            state,
            AGENT_NAME,
            f"retrieved {len(results)} chunk(s) covering {len(ordered)} scheme(s) "
            f"using {retriever.retrieval_mode}"
            + (f"; top match: {truncate(results[0].chunk.scheme_name, 60)}" if results else ""),
        )
    )
    return update
