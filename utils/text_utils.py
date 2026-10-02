"""Small text helpers used by the retriever and the profile parser."""

from __future__ import annotations

import re
from typing import Iterable

# Very small English stop-word list. Enough for a small curated knowledge base.
STOP_WORDS: set[str] = {
    "a", "about", "am", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "get", "had", "has", "have", "he",
    "her", "here", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "me",
    "my", "need", "no", "not", "of", "on", "or", "our", "please", "she", "should", "so",
    "some", "tell", "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "to", "up", "was", "we", "were", "what", "when", "which", "who", "why", "will",
    "with", "would", "you", "your", "am", "i'm", "im",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Synonyms so a user question matches the knowledge-base wording.
SYNONYMS: dict[str, str] = {
    "mca": "postgraduate",
    "mba": "postgraduate",
    "mtech": "postgraduate",
    "masters": "postgraduate",
    "master": "postgraduate",
    "pg": "postgraduate",
    "btech": "undergraduate",
    "btech": "undergraduate",
    "bca": "undergraduate",
    "bsc": "undergraduate",
    "bcom": "undergraduate",
    "ba": "undergraduate",
    "bachelor": "undergraduate",
    "ug": "undergraduate",
    "polytechnic": "diploma",
    "phd": "phd",
    "doctorate": "phd",
    "doctoral": "phd",
    "mphil": "mphil",
    "girls": "female",
    "girl": "female",
    "women": "female",
    "woman": "female",
    "boy": "male",
    "ladies": "female",
    "disabled": "disability",
    "differently": "disability",
    "handicapped": "disability",
    "divyang": "disability",
    "lakh": "lakh",
    "lakhs": "lakh",
    "crore": "crore",
    "crores": "crore",
    "income": "income",
    "salary": "income",
    "fees": "tuition",
    "tuition": "tuition",
    "money": "benefit",
    "stipend": "benefit",
    "scholarship": "scholarship",
    "scholarships": "scholarship",
    "aid": "benefit",
}


def normalise_text(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def tokenize(text: str, apply_synonyms: bool = True) -> list[str]:
    """
    Split text into search tokens.

    Stop words are removed and simple singular forms are folded so that
    "students" matches "student".
    """
    raw_tokens = _TOKEN_RE.findall(normalise_text(text))
    tokens: list[str] = []
    for token in raw_tokens:
        if token in STOP_WORDS:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        if apply_synonyms:
            token = SYNONYMS.get(token, token)
        if token in STOP_WORDS:
            continue
        tokens.append(token)
    return tokens


def tokenize_many(texts: Iterable[str]) -> list[str]:
    tokens: list[str] = []
    for text in texts:
        tokens.extend(tokenize(text))
    return tokens


def truncate(text: str, limit: int = 240) -> str:
    """Shorten text for logs / previews."""
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "\u2026"
