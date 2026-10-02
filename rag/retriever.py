"""
The retriever: the "R" of Retrieval-Augmented Generation.

Two scorers are combined:

  1. **BM25 (lexical)** - a classic, dependency-free keyword scorer. It always
     works, is fast, and is very good at matching scheme jargon such as
     "post matric" or "OBC".
  2. **Cosine similarity over sentence embeddings** - optional. It catches
     paraphrases such as "money for girls in engineering" -> Pragati. The model
     is loaded in a background thread, so if it cannot be downloaded the app
     simply keeps using BM25.

Both scores are min-max normalised and blended, then the best chunks are
returned. Results are always traceable back to a `scheme_id`, which is what
lets the answer agent guarantee "no invention".
"""

from __future__ import annotations

import math
import threading
from typing import Iterable, Optional, Sequence

from backend.config import Settings, settings as app_settings
from models.profile import UserProfile
from models.scheme import RetrievalChunk, RetrievalResult, Scheme
from rag.chunking import SchemeChunker
from rag.loader import SchemeStore, get_scheme_store
from utils.logging_utils import get_logger
from utils.text_utils import tokenize, truncate

logger = get_logger("rag.retriever")

# BM25 tuning parameters (standard defaults).
BM25_K1 = 1.5
BM25_B = 0.75

# --- Relevance floors -------------------------------------------------------
# Scores are min-max normalised for blending, which means a weak match can look
# like a perfect one. These absolute floors are applied BEFORE normalisation so
# that an unrelated question ("do you have schemes for a Mars rover?") returns
# nothing instead of the least-bad chunk.
MIN_LEXICAL_SCORE = 0.5   # raw BM25 score
MIN_SEMANTIC_SCORE = 0.30  # cosine similarity


class BM25Index:
    """Minimal BM25 implementation over pre-tokenised documents."""

    def __init__(self, documents: Sequence[Sequence[str]]) -> None:
        self.documents = list(documents)
        self.doc_lengths = [len(doc) for doc in self.documents]
        self.avg_doc_length = (
            sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        )
        self._term_frequencies: list[dict[str, int]] = [dict() for _ in self.documents]
        document_frequency: dict[str, int] = {}

        for index, document in enumerate(self.documents):
            frequencies = self._term_frequencies[index]
            for token in document:
                frequencies[token] = frequencies.get(token, 0) + 1
            for token in frequencies:
                document_frequency[token] = document_frequency.get(token, 0) + 1

        total_documents = max(len(self.documents), 1)
        self._idf: dict[str, float] = {
            term: math.log(1 + (total_documents - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def score(self, query_tokens: Sequence[str], index: int) -> float:
        frequencies = self._term_frequencies[index]
        doc_length = self.doc_lengths[index] or 1
        total = 0.0
        for token in query_tokens:
            term_frequency = frequencies.get(token)
            if not term_frequency:
                continue
            idf = self._idf.get(token, 0.0)
            denominator = term_frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * (doc_length / (self.avg_doc_length or 1))
            )
            total += idf * (term_frequency * (BM25_K1 + 1)) / denominator
        return total


def _min_max_normalise(values: list[float]) -> list[float]:
    if not values:
        return []
    lowest, highest = min(values), max(values)
    if highest - lowest < 1e-9:
        return [1.0 if highest > 0 else 0.0 for _ in values]
    span = highest - lowest
    return [(value - lowest) / span for value in values]


class SchemeRetriever:
    """Hybrid (BM25 + optional embeddings) retriever over the scheme chunks."""

    def __init__(self, store: Optional[SchemeStore] = None, config: Optional[Settings] = None) -> None:
        self.settings = config or app_settings
        self.store: SchemeStore = store or get_scheme_store()
        self.chunker = SchemeChunker()

        # --- build chunks --------------------------------------------------
        self.chunks: list[RetrievalChunk] = []
        for scheme in self.store.all():
            self.chunks.extend(self.chunker.build(scheme))
        self.chunks = self.chunks[: max(self.settings.rag_max_chunks, len(self.chunks))]

        # --- lexical index (fast, always available) ------------------------
        self.bm25 = BM25Index([tokenize(chunk.text) for chunk in self.chunks])

        # --- optional dense index -----------------------------------------
        self.embeddings: Optional[list[list[float]]] = None
        self._embedder = None
        self._embeddings_lock = threading.Lock()
        self._embeddings_state = "disabled"  # disabled | loading | ready | failed
        if self.settings.embedding_enabled:
            self._start_embedding_load()

    # ------------------------------------------------------------------
    # Embeddings (optional, never blocks a request)
    # ------------------------------------------------------------------
    def _start_embedding_load(self) -> None:
        self._embeddings_state = "loading"

        def _worker() -> None:
            try:
                from sentence_transformers import SentenceTransformer  # heavy import

                model = SentenceTransformer(self.settings.embedding_model)
                vectors = model.encode(
                    [chunk.text for chunk in self.chunks],
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # cosine similarity == dot product
                    show_progress_bar=False,
                )
                with self._embeddings_lock:
                    self.embeddings = [list(map(float, vector)) for vector in vectors]
                    self._embedder = model
                    self._embeddings_state = "ready"
                logger.info("Dense retrieval ready (%s)", self.settings.embedding_model)
            except Exception as exc:  # pragma: no cover - environment dependent
                with self._embeddings_lock:
                    self._embeddings_state = "failed"
                logger.warning(
                    "Dense retrieval unavailable (%s: %s). Falling back to BM25 only.",
                    type(exc).__name__,
                    truncate(str(exc), 160),
                )

        threading.Thread(target=_worker, name="embedding-loader", daemon=True).start()

    @property
    def retrieval_mode(self) -> str:
        with self._embeddings_lock:
            state = self._embeddings_state
        if state == "ready":
            return "hybrid (BM25 + embeddings)"
        if state == "loading":
            return "BM25 (embeddings still loading)"
        if state == "failed":
            return "BM25 (embeddings unavailable)"
        return "BM25 (embeddings disabled)"

    def _dense_scores(self, query: str) -> Optional[list[float]]:
        with self._embeddings_lock:
            if self._embeddings_state != "ready" or self._embedder is None:
                return None
            model, vectors = self._embedder, self.embeddings
        try:
            query_vector = model.encode(
                [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
            )[0]
            return [float(sum(a * b for a, b in zip(vectors[i], query_vector))) for i in range(len(vectors))]
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Dense scoring failed, using BM25 only: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        scheme_ids: Optional[Iterable[str]] = None,
    ) -> list[RetrievalResult]:
        """Return the best matching chunks for a free-text query."""
        if not self.chunks:
            return []

        top_k = top_k or self.settings.rag_top_k
        allowed_ids = {str(item).upper() for item in scheme_ids} if scheme_ids else None
        candidate_indices = [
            index
            for index, chunk in enumerate(self.chunks)
            if allowed_ids is None or chunk.scheme_id.upper() in allowed_ids
        ]
        if not candidate_indices:
            return []

        query_tokens = tokenize(query)
        lexical = [self.bm25.score(query_tokens, index) for index in candidate_indices]
        dense = self._dense_scores(query)
        if dense is None:
            semantic = [0.0] * len(candidate_indices)
        else:
            semantic = [dense[index] for index in candidate_indices]

        # Step 1 - absolute relevance filter, before any normalisation.
        survivors: list[int] = []
        for position, index in enumerate(candidate_indices):
            lexical_ok = lexical[position] >= MIN_LEXICAL_SCORE
            semantic_ok = semantic[position] >= MIN_SEMANTIC_SCORE
            if lexical_ok or semantic_ok:
                survivors.append(position)

        if not survivors:
            logger.info("retrieve: no chunk passed the relevance floor for %r", query[:80])
            return []

        # Step 2 - normalise and blend, but only across the survivors.
        normalised_lexical = _min_max_normalise([lexical[position] for position in survivors])
        normalised_semantic = _min_max_normalise([semantic[position] for position in survivors])
        lexical_weight = self.settings.lexical_weight

        results: list[RetrievalResult] = []
        for offset, position in enumerate(survivors):
            index = candidate_indices[position]
            blended = (
                lexical_weight * normalised_lexical[offset]
                + (1 - lexical_weight) * normalised_semantic[offset]
            )
            chunk = self.chunks[index]
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=round(blended, 6),
                    lexical_score=round(lexical[position], 4),
                    semantic_score=round(semantic[position], 4),
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)

        # Keep at most `top_k` chunks per scheme so the prompt is balanced.
        per_scheme: dict[str, int] = {}
        selected: list[RetrievalResult] = []
        max_per_scheme = 2
        for result in results:
            scheme_id = result.chunk.scheme_id
            if per_scheme.get(scheme_id, 0) >= max_per_scheme:
                continue
            per_scheme[scheme_id] = per_scheme.get(scheme_id, 0) + 1
            selected.append(result)
            if len(selected) >= top_k:
                break

        return selected

    def build_profile_query(self, profile: UserProfile) -> str:
        """
        Turn a profile into a search query.

        This is what makes the app feel personal even when the user only types
        a vague question such as "what can I apply for?".
        """
        parts: list[str] = []
        if profile.education_level:
            parts.append(profile.education_level)
        if profile.course:
            parts.append(profile.course)
        if profile.category:
            parts.append(profile.category)
        if profile.state:
            parts.append(profile.state)
        if profile.gender:
            parts.append(profile.gender)
        if profile.student_status:
            parts.append(profile.student_status)
        if profile.has_disability():
            parts.append("differently abled disability special abilities")
        if profile.age:
            parts.append(f"{profile.age} years old")
        if profile.family_income is not None:
            lakhs = profile.family_income / 100_000
            parts.append(f"family income {lakhs:.1f} lakh per year income limit")
        return " ".join(parts)

    def retrieve_for_profile(
        self,
        profile: UserProfile,
        question: str = "",
        top_k: Optional[int] = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve with a combined query: the user's own words + the profile.

        When the question carries real signal it gets extra weight by being
        repeated in the query string.
        """
        top_k = top_k or self.settings.rag_top_k
        parts = [self.build_profile_query(profile)]
        if question:
            parts.append(question)
            parts.append(question)  # user intent weighs more
        return self.retrieve(" ".join(part for part in parts if part), top_k=top_k)

    # ------------------------------------------------------------------
    # Introspection used by /health and the UI debug panel
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        return {
            "schemes": len(self.store),
            "chunks": len(self.chunks),
            "lexical_weight": self.settings.lexical_weight,
            "embedding_model": self.settings.embedding_model if self.settings.embedding_enabled else None,
            "embedding_state": self._embeddings_state,
            "mode": self.retrieval_mode,
        }


_RETRIEVER: Optional[SchemeRetriever] = None
_RETRIEVER_LOCK = threading.Lock()


def get_retriever() -> SchemeRetriever:
    """Lazily build (and cache) the retriever."""
    global _RETRIEVER
    if _RETRIEVER is None:
        with _RETRIEVER_LOCK:
            if _RETRIEVER is None:
                _RETRIEVER = SchemeRetriever()
    return _RETRIEVER
