"""
Modular LLM layer.

To add a new provider: subclass `BaseLLMClient`, implement `chat`, and register
it in `llm/factory.py`. Nothing else in the codebase needs to change.
"""

from llm.base import BaseLLMClient, LLMError, LLMResponse
from llm.openai_compatible import OpenAICompatibleClient
from llm.grok_client import GrokClient
from llm.groq_client import GroqClient
from llm.openai_client import OpenAIClient
from llm.offline_client import OfflineClient
from llm.factory import get_llm_client, chat_with_fallback

__all__ = [
    "BaseLLMClient",
    "LLMError",
    "LLMResponse",
    "OpenAICompatibleClient",
    "GrokClient",
    "GroqClient",
    "OpenAIClient",
    "OfflineClient",
    "get_llm_client",
    "chat_with_fallback",
]
