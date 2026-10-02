"""OpenAI provider - included to demonstrate provider swapping.

Configure with:
    OPENAI_API_KEY=your_key_here
"""

from __future__ import annotations

from typing import Optional

from backend.config import Settings, settings as app_settings
from llm.openai_compatible import OpenAICompatibleClient


class OpenAIClient(OpenAICompatibleClient):
    def __init__(self, settings: Optional[Settings] = None) -> None:
        config = settings or app_settings
        super().__init__(
            name="openai",
            api_key=config.openai_api_key,
            model=config.openai_model,
            base_url=config.openai_base_url,
            settings=config,
        )
