"""
Shared client for OpenAI-compatible chat-completion APIs.

Grok (xAI), Groq and OpenAI all speak the same `/chat/completions` dialect, so
one small `httpx` implementation covers all three without adding a heavy SDK.
"""

from __future__ import annotations

import httpx
from typing import Optional

from backend.config import Settings, settings as app_settings
from llm.base import BaseLLMClient, LLMError, LLMResponse


class OpenAICompatibleClient(BaseLLMClient):
    """POST to `{base_url}/chat/completions` with a bearer token."""

    def __init__(
        self,
        name: str,
        api_key: Optional[str],
        model: str,
        base_url: str,
        settings: Optional[Settings] = None,
    ) -> None:
        self.name = name
        self.api_key = (api_key or "").strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.settings = settings or app_settings

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.available:
            raise LLMError(f"{self.name}: no API key configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.settings.llm_temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMError(f"{self.name}: request timed out after {self.settings.llm_timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.name}: network error - {exc}") from exc

        if response.status_code != 200:
            # Never log the key, only the provider's error message.
            raise LLMError(
                f"{self.name}: HTTP {response.status_code} - {response.text[:300]}"
            )

        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError) as exc:
            raise LLMError(f"{self.name}: unexpected response shape") from exc

        return LLMResponse(
            text=text.strip(),
            provider=self.name,
            model=self.model,
            used_llm=True,
            raw={"usage": data.get("usage", {})},
        )
