"""
Application configuration.

Every setting is read from an environment variable (or a local `.env` file).
Nothing secret is hardcoded in the code. See `.env.example` for the full list.

Run the backend from the project root, e.g.
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# backend/config.py  ->  backend/  ->  project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR: Path = PROJECT_ROOT / "knowledge_base"

# Text shown everywhere in the UI so sample data is never mistaken for
# verified government information.
DATA_DISCLAIMER: str = (
    "Demo/sample dataset for learning and evaluation only. Scheme details, "
    "income ceilings and deadlines are illustrative and are NOT verified against "
    "official notifications. Always confirm on the official government portal "
    "before applying."
)


# ---------------------------------------------------------------------------
# Tiny .env loader (kept intentionally simple so it is easy to follow)
# ---------------------------------------------------------------------------
def _load_dotenv() -> None:
    """Read `KEY=value` pairs from the project-root `.env` file, if present."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Real environment variables always win over the .env file.
        os.environ.setdefault(key, value)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Settings object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the app configuration."""

    # --- App metadata -----------------------------------------------------
    app_name: str = "Government Scheme Assistant"
    app_version: str = "1.0.0"
    environment: str = "development"

    # --- Server -----------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )

    # --- LLM providers (all optional) -------------------------------------
    # `LLM_PROVIDER=auto` picks the first provider that has a key available:
    # grok -> groq -> openai -> offline (no LLM, retrieval-only answers).
    llm_provider: str = "auto"
    grok_api_key: str | None = None
    grok_model: str = "grok-4.6"
    grok_base_url: str = "https://api.x.ai/v1"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 900
    llm_timeout_seconds: int = 60

    # --- Knowledge base ---------------------------------------------------
    knowledge_base_file: str = "schemes.jsonl"

    # --- RAG --------------------------------------------------------------
    rag_top_k: int = 6
    rag_max_chunks: int = 60
    lexical_weight: float = 0.7          # BM25 weight in the hybrid score
    embedding_enabled: bool = True       # falls back to BM25-only if unavailable
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @property
    def knowledge_base_path(self) -> Path:
        return KNOWLEDGE_BASE_DIR / self.knowledge_base_file

    @property
    def data_disclaimer(self) -> str:
        return DATA_DISCLAIMER


def get_settings() -> Settings:
    """Build a `Settings` instance from environment variables."""
    _load_dotenv()

    return Settings(
        app_name=os.getenv("APP_NAME", "Government Scheme Assistant"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=_as_int(os.getenv("PORT"), 8000),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cors_origins=_as_list(
            os.getenv("CORS_ORIGINS"),
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            ],
        ),
        llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
        grok_api_key=os.getenv("GROK_API_KEY") or None,
        grok_model=os.getenv("GROK_MODEL", "grok-4.6"),
        grok_base_url=os.getenv("GROK_BASE_URL", "https://api.x.ai/v1"),
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        llm_temperature=_as_float(os.getenv("LLM_TEMPERATURE"), 0.1),
        llm_max_tokens=_as_int(os.getenv("LLM_MAX_TOKENS"), 900),
        llm_timeout_seconds=_as_int(os.getenv("LLM_TIMEOUT_SECONDS"), 60),
        knowledge_base_file=os.getenv("KNOWLEDGE_BASE_FILE", "schemes.jsonl"),
        rag_top_k=_as_int(os.getenv("RAG_TOP_K"), 6),
        rag_max_chunks=_as_int(os.getenv("RAG_MAX_CHUNKS"), 60),
        lexical_weight=_as_float(os.getenv("RAG_LEXICAL_WEIGHT"), 0.7),
        embedding_enabled=_as_bool(os.getenv("EMBEDDING_ENABLED"), True),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )


settings = get_settings()
