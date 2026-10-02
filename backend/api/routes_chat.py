"""`/chat` endpoint: the AI assistant."""

from __future__ import annotations

from fastapi import APIRouter

from models.api import ChatRequest, ChatResponse
from services.chat_service import handle_chat

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="Ask the AI assistant a question")
def chat(request: ChatRequest) -> ChatResponse:
    """
    Runs the full LangGraph workflow:
    profile extraction -> retrieval -> eligibility -> recommendation -> response.
    """
    return handle_chat(request)
