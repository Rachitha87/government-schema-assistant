"""Grok (xAI) provider - the default LLM for this project.

Configure with:
    GROK_API_KEY=your_key_here
    GROK_MODEL=grok-4.6
"""

from __future__ import annotations

from typing import Optional

from backend.config import Settings, settings as app_settings
from llm.openai_compatible import OpenAICompatibleClient


class GrokClient(OpenAICompatibleClient):
    def __init__(self, settings: Optional[Settings] = None) -> None:
        config = settings or app_settings
        super().__init__(
            name="grok",
            api_key=config.grok_api_key,
            model=config.grok_model,
            base_url=config.grok_base_url,
            settings=config,
        )
