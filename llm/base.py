"""Common LLM interface shared by every provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


class LLMError(RuntimeError):
    """Raised when a provider call fails (bad key, timeout, rate limit...)."""


@dataclass
class LLMResponse:
    """Normalised provider response."""

    text: str
    provider: str
    model: str
    used_llm: bool = True
    error: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


class BaseLLMClient(ABC):
    """
    Every provider implements this one method.

    Attributes:
        name:  short provider id shown in the UI ("grok", "groq", "offline"...)
        model: model id actually used
    """

    name: str = "base"
    model: str = "unknown"

    @property
    def available(self) -> bool:
        """True when this provider is usable (e.g. an API key is present)."""
        return True

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a chat-completion request and return the assistant text."""

    def health(self) -> dict:
        return {"provider": self.name, "model": self.model, "available": self.available}
