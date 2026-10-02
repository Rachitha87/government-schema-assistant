"""
Read-only scheme access: browsing, searching and filtering.

Search uses both plain substring matching and the RAG retriever's BM25 score, so
"girls engineering" finds Pragati even though those exact words are not in the
scheme name.
"""

from __future__ import annotations

from typing import Optional

from backend.config import settings
from models.scheme import Scheme, SchemeSummary
from rag.loader import get_scheme_store
from rag.retriever import get_retriever
from utils.logging_utils import get_logger
from utils.normalize import (
    education_matches,
    normalise_category,
    normalise_education_level,
    normalise_gender,
    normalise_state,
)
from utils.text_utils import tokenize, truncate

logger = get_logger("services.schemes")


def _matches_filters(scheme: Scheme, **filters) -> bool:
    """Structured filtering on the fields the UI exposes."""
    for key, value in filters.items():
        if value in (None, "", []):
            continue

        if key == "state":
            if "All" not in scheme.states and normalise_state(value) not in scheme.states:
                return False
        elif key == "category":
            if "All" not in scheme.categories and normalise_category(value) not in scheme.categories:
                return False
        elif key == "gender":
            if scheme.gender.lower() != "all" and normalise_gender(value) != scheme.gender:
                return False
        elif key == "education_level":
            if not education_matches(normalise_education_level(value), scheme.education_levels):
                return False
        elif key == "provider":
            if value.lower() not in scheme.provider.lower():
                return False
        elif key == "scheme_type":
            keyword = str(value).lower()
            if keyword == "scholarship" and "scholarship" not in scheme.name.lower():
                return False
            if keyword == "fellowship" and "fellowship" not in scheme.name.lower():
                return False
        elif key == "data_status":
            if str(value).lower() != scheme.data_status.lower():
                return False
    return True


def list_schemes(
    q: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    gender: Optional[str] = None,
    education_level: Optional[str] = None,
    provider: Optional[str] = None,
    scheme_type: Optional[str] = None,
    data_status: Optional[str] = None,
    limit: int = 50,
) -> list[SchemeSummary]:
    """Return the schemes that match the given filters, best match first."""
    store = get_scheme_store()
    candidates = [
        scheme
        for scheme in store.all()
        if _matches_filters(
            scheme,
            state=state,
            category=category,
            gender=gender,
            education_level=education_level,
            provider=provider,
            scheme_type=scheme_type,
            data_status=data_status,
        )
    ]

    if q and q.strip():
        query = q.strip()
        query_lower = query.lower()

        # Cheap exact-ish pass first.
        exact = [
            scheme
            for scheme in candidates
            if query_lower in scheme.name.lower()
            or query_lower in scheme.description.lower()
            or query_lower in " ".join(scheme.tags).lower()
        ]

        # Then a scored pass so synonyms ("girls in engineering") also match.
        retriever = get_retriever()
        allowed_ids = [scheme.scheme_id for scheme in candidates]
        scored: list[tuple[float, Scheme]] = []
        if allowed_ids:
            for result in retriever.retrieve(query, top_k=len(allowed_ids) * 2, scheme_ids=allowed_ids):
                scheme = store.get(result.chunk.scheme_id)
                if scheme and result.score > 0:
                    scored.append((result.score, scheme))
        scored.sort(key=lambda item: item[0], reverse=True)

        ranked: list[Scheme] = []
        for scheme in exact + [scheme for _, scheme in scored]:
            if scheme not in ranked:
                ranked.append(scheme)
        candidates = ranked

        # A search should stay useful: only keep genuine matches, and never
        # return more results than there are schemes in the knowledge base.
        if not exact:
            candidates = candidates[: max(min(limit, 12), 1)]
    else:
        # No query: keep a stable, useful order (scholarships first, then name).
        candidates.sort(key=lambda scheme: ("scholarship" not in scheme.name.lower(), scheme.name.lower()))

    logger.info("list_schemes: %d result(s) for query=%r", len(candidates), q)
    return [scheme.to_summary() for scheme in candidates[: max(limit, 1)]]


def get_scheme(scheme_id: str) -> Optional[Scheme]:
    """Fetch one scheme by id (case-insensitive)."""
    scheme = get_scheme_store().get(scheme_id)
    if scheme:
        logger.info("get_scheme: %s", scheme.scheme_id)
    return scheme


def list_filters() -> dict:
    """Option lists for the Browse page dropdowns."""
    store = get_scheme_store()
    return {
        "states": store.states(),
        "categories": store.categories(),
        "genders": ["Female", "Male", "Other"],
        "education_levels": store.education_levels(),
        "providers": store.providers(),
        "scheme_types": ["scholarship", "fellowship"],
        "data_statuses": ["sample-unverified", "officially-published"],
    }


def knowledge_base_stats() -> dict:
    store = get_scheme_store()
    retriever = get_retriever()
    return {
        "schemes": len(store),
        "sample_data_schemes": store.sample_data_count(),
        "providers": len(store.providers()),
        "retrieval": retriever.stats(),
        "file": settings.knowledge_base_file,
        "path": str(store.source_path),
    }
