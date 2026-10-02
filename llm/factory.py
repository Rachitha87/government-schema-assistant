"""
LLM factory.

`LLM_PROVIDER` decides which client is used:

    auto      (default) grok -> groq -> openai -> offline
    grok                 only Grok (falls back to offline if the key is missing)
    groq / openai        the respective provider
    offline              never call a network API (free, deterministic, grounded)

Keys are read from the environment only. Nothing is hardcoded.
"""

from __future__ import annotations

import threading
from typing import Optional

from backend.config import Settings, settings as app_settings
from llm.base import BaseLLMClient, LLMError, LLMResponse
from llm.grok_client import GrokClient
from llm.groq_client import GroqClient
from llm.offline_client import OfflineClient
from llm.openai_client import OpenAIClient
from utils.logging_utils import get_logger

logger = get_logger("llm.factory")


def _build_client(provider: str, config: Settings) -> BaseLLMClient:
    provider = (provider or "auto").strip().lower()

    if provider == "offline":
        return OfflineClient()

    if provider == "grok":
        return GrokClient(config)
    if provider == "groq":
        return GroqClient(config)
    if provider == "openai":
        return OpenAIClient(config)

    # auto: first provider with a key wins
    if config.grok_api_key:
        return GrokClient(config)
    if config.groq_api_key:
        return GroqClient(config)
    if config.openai_api_key:
        return OpenAIClient(config)
    return OfflineClient()


_CLIENT: Optional[BaseLLMClient] = None
_LOCK = threading.Lock()


def get_llm_client(config: Optional[Settings] = None) -> BaseLLMClient:
    """Return the process-wide LLM client (built once)."""
    global _CLIENT
    if _CLIENT is None:
        with _LOCK:
            if _CLIENT is None:
                settings = config or app_settings
                client = _build_client(settings.llm_provider, settings)
                if client.name == "offline":
                    logger.warning(
                        "No LLM API key found (GROK_API_KEY / GROQ_API_KEY / OPENAI_API_KEY). "
                        "Running in retrieval-only mode: answers are templated but fully grounded."
                    )
                else:
                    logger.info("LLM provider: %s (model=%s)", client.name, client.model)
                _CLIENT = client
    return _CLIENT


def reset_llm_client() -> None:
    """Used by tests and by the `Reload config` dev endpoint."""
    global _CLIENT
    with _LOCK:
        _CLIENT = None


def chat_with_fallback(
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMResponse:
    """
    Call the configured LLM, but never fail the request.

    If the provider errors (bad key, timeout, rate limit) the offline
    retrieval-only client produces the answer instead and the error is attached
    to the response so the UI can show it.
    """
    client = get_llm_client()

    if client.name != "offline":
        try:
            return client.chat(messages, temperature=temperature, max_tokens=max_tokens)
        except LLMError as exc:
            logger.warning("LLM call failed (%s). Falling back to offline mode.", exc)
            fallback = OfflineClient().chat(messages)
            fallback.error = str(exc)
            return fallback
        except Exception as exc:  # pragma: no cover - unexpected provider bug
            logger.exception("Unexpected LLM failure: %s", exc)
            fallback = OfflineClient().chat(messages)
            fallback.error = f"unexpected error: {exc}"
            return fallback

    return client.chat(messages, temperature=temperature, max_tokens=max_tokens)
