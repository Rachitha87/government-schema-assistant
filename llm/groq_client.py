"""Groq provider - a free-tier-friendly alternative to Grok.

Configure with:
    GROQ_API_KEY=your_key_here
    GROQ_MODEL=llama-3.3-70b-versatile
"""

from __future__ import annotations

from typing import Optional

from backend.config import Settings, settings as app_settings
from llm.openai_compatible import OpenAICompatibleClient


class GroqClient(OpenAICompatibleClient):
    def __init__(self, settings: Optional[Settings] = None) -> None:
        config = settings or app_settings
        super().__init__(
            name="groq",
            api_key=config.groq_api_key,
            model=config.groq_model,
            base_url=config.groq_base_url,
            settings=config,
        )
