"""
Chunking: turn each scheme into small, self-contained text blocks.

Why chunk at all? A whole scheme record is longer than needed for one retrieval
step, and mixing "eligibility" text with "benefits" text hurts ranking. Each
chunk therefore covers one section and repeats the scheme name and provider so
it still makes sense on its own.
"""

from __future__ import annotations

from models.scheme import RetrievalChunk, Scheme
from utils.text_utils import tokenize


class SchemeChunker:
    """Builds the retrievable chunks for one scheme."""

    #: Order matters only for readability of the final prompt.
    SECTIONS = ("overview", "eligibility", "benefits", "application")

    @staticmethod
    def _header(scheme: Scheme) -> str:
        return f"Scheme: {scheme.name} (ID: {scheme.scheme_id}). Provider: {scheme.provider}."

    def build(self, scheme: Scheme) -> list[RetrievalChunk]:
        chunks: list[RetrievalChunk] = []

        def _add(section: str, body: str) -> None:
            body = " ".join(str(body or "").split())
            if not body:
                return
            chunks.append(
                RetrievalChunk(
                    chunk_id=f"{scheme.scheme_id}::{section}",
                    scheme_id=scheme.scheme_id,
                    scheme_name=scheme.name,
                    provider=scheme.provider,
                    section=section,
                    text=f"{self._header(scheme)} {body}",
                )
            )

        _add(
            "overview",
            f"{scheme.description} Education level: {scheme.education_level}."
            + (f" Keywords: {', '.join(scheme.tags)}." if scheme.tags else ""),
        )
        _add(
            "eligibility",
            f"Eligibility criteria: {scheme.eligibility}"
            f" Income limit: {scheme.income_limit}."
            f" Age range: {self._age_text(scheme)}."
            f" Eligible categories: {', '.join(scheme.categories) or 'All'}."
            f" Applicable in: {', '.join(scheme.states) or 'All India'}."
            f" Education level required: {', '.join(scheme.education_levels) or 'Any'}."
            f" Gender: {scheme.gender}."
            + (" Only for persons with disability." if scheme.disability_required else ""),
        )
        _add("benefits", f"Benefits provided: {scheme.benefits}")
        _add(
            "application",
            f"Application deadline: {scheme.deadline}"
            f" Official application link: {scheme.application_link or 'not recorded in the knowledge base'}."
            f" Data status: {scheme.data_status}."
            + (f" Note: {scheme.notes}" if scheme.notes else ""),
        )
        return chunks

    @staticmethod
    def _age_text(scheme: Scheme) -> str:
        if scheme.min_age is None and scheme.max_age is None:
            return "not specified"
        if scheme.min_age is not None and scheme.max_age is not None:
            return f"{scheme.min_age} to {scheme.max_age} years"
        if scheme.min_age is not None:
            return f"{scheme.min_age} years and above"
        return f"up to {scheme.max_age} years"


def build_chunks(scheme: Scheme) -> list[RetrievalChunk]:
    """Module-level convenience wrapper around `SchemeChunker`."""
    return SchemeChunker().build(scheme)


def chunk_tokens(chunk: RetrievalChunk) -> list[str]:
    """Tokens used by the lexical retriever (text + tags already merged)."""
    return tokenize(chunk.text)
