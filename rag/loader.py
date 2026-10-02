"""
Knowledge-base loader.

The knowledge base is a simple, human-editable JSONL file (one JSON object per
line). A plain JSON array is also supported so a fresher can paste data from
anywhere. Nothing here talks to an LLM - it is pure file reading.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.config import settings
from models.scheme import Scheme
from utils.logging_utils import get_logger

logger = get_logger("rag.loader")


class SchemeStore:
    """
    In-memory store of the knowledge base.

    Loaded once at startup and reused, because the file is read-only and small.
    """

    def __init__(self, schemes: list[Scheme], source_path: Path) -> None:
        self.schemes: list[Scheme] = schemes
        self.source_path: Path = source_path
        self._by_id: dict[str, Scheme] = {scheme.scheme_id: scheme for scheme in schemes}

    # -- read ---------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.schemes)

    def all(self) -> list[Scheme]:
        return list(self.schemes)

    def get(self, scheme_id: str) -> Optional[Scheme]:
        """Case-insensitive lookup by id, e.g. 'sch001' -> scheme."""
        if not scheme_id:
            return None
        return self._by_id.get(str(scheme_id).strip().upper())

    def providers(self) -> list[str]:
        return sorted({scheme.provider for scheme in self.schemes})

    def categories(self) -> list[str]:
        values: set[str] = set()
        for scheme in self.schemes:
            values.update(scheme.categories)
        values.discard("All")
        return sorted(values)

    def states(self) -> list[str]:
        values: set[str] = set()
        for scheme in self.schemes:
            values.update(scheme.states)
        values.discard("All")
        return sorted(values)

    def education_levels(self) -> list[str]:
        values: set[str] = set()
        for scheme in self.schemes:
            values.update(scheme.education_levels)
        return sorted(values)

    def sample_data_count(self) -> int:
        return sum(1 for scheme in self.schemes if scheme.is_sample_data)


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------
def _parse_records(raw_text: str) -> list[dict]:
    """Parse either JSONL or a JSON array into a list of dicts."""
    stripped = raw_text.strip()
    if not stripped:
        return []

    if stripped[0] == "[":
        data = json.loads(stripped)
        return [item for item in data if isinstance(item, dict)]

    records: list[dict] = []
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON on line {line_number} of the knowledge base: {exc}"
            ) from exc
        if isinstance(item, dict):
            records.append(item)
    return records


def load_schemes(path: Optional[Path | str] = None) -> list[Scheme]:
    """Read and validate the knowledge base into `Scheme` objects."""
    kb_path = Path(path) if path else settings.knowledge_base_path
    if not kb_path.exists():
        raise FileNotFoundError(
            f"Knowledge base file not found: {kb_path}. "
            "Set KNOWLEDGE_BASE_FILE or create knowledge_base/schemes.jsonl."
        )

    raw_text = kb_path.read_text(encoding="utf-8")
    records = _parse_records(raw_text)

    schemes: list[Scheme] = []
    for index, record in enumerate(records, start=1):
        record.setdefault("scheme_id", f"SCH{index:03d}")
        # Accept both list and comma-separated string values in the JSONL file.
        for key in ("categories", "states", "education_levels", "course_keywords", "tags"):
            if isinstance(record.get(key), str):
                record[key] = [
                    part.strip()
                    for part in record[key].split(",")
                    if part.strip() and part.strip() != "All"
                ] or ([] if key in ("course_keywords", "tags") else ["All"])
        try:
            schemes.append(Scheme(**record))
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Skipping invalid record %s in %s: %s", record.get("scheme_id"), kb_path, exc)

    if not schemes:
        raise ValueError(f"No valid schemes found in {kb_path}")

    logger.info("Loaded %d schemes from %s", len(schemes), kb_path)
    return schemes


_STORE: Optional[SchemeStore] = None


def get_scheme_store() -> SchemeStore:
    """Lazily build (and cache) the scheme store."""
    global _STORE
    if _STORE is None:
        _STORE = SchemeStore(load_schemes(), settings.knowledge_base_path)
    return _STORE
