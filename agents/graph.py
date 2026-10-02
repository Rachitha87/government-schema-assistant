"""
The LangGraph agent workflow.

    User Profile  ->  Scheme Retrieval  ->  Eligibility Checking
                 ->  Recommendation    ->  Response

Every node is a plain Python function in this package (`agents/*_agent.py`),
which means the graph is easy to read *and* easy to unit test without a
framework.

`langgraph` is used when it is installed. If it is not, `run_workflow` falls
back to a plain-python runner that executes the same nodes in the same order -
so the project never hard-fails because of a missing optional dependency.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from agents import (
    eligibility_agent,
    profile_agent,
    recommendation_agent,
    response_agent,
    retrieval_agent,
)
from agents.state import AgentState, new_state
from backend.config import settings
from models.profile import UserProfile
from utils.logging_utils import get_logger

logger = get_logger("agents.graph")

try:  # LangGraph is the intended runtime for this project.
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    LANGGRAPH_AVAILABLE = False


#: Order in which the agents run. Used by the fallback runner as well.
PIPELINE: list[tuple[str, Callable[[AgentState], dict[str, Any]]]] = [
    ("user_profile_agent", profile_agent.run),
    ("scheme_retrieval_agent", retrieval_agent.run),
    ("eligibility_checking_agent", eligibility_agent.run),
    ("recommendation_agent", recommendation_agent.run),
    ("response_agent", response_agent.run),
]


_compiled_graph = None


def build_graph():
    """
    Compile the LangGraph state graph.

    Returns ``None`` when LangGraph is not installed.
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("user_profile_agent", profile_agent.run)
    graph.add_node("scheme_retrieval_agent", retrieval_agent.run)
    graph.add_node("eligibility_checking_agent", eligibility_agent.run)
    graph.add_node("recommendation_agent", recommendation_agent.run)
    graph.add_node("response_agent", response_agent.run)

    graph.set_entry_point("user_profile_agent")
    graph.add_edge("user_profile_agent", "scheme_retrieval_agent")
    graph.add_edge("scheme_retrieval_agent", "eligibility_checking_agent")
    graph.add_edge("eligibility_checking_agent", "recommendation_agent")
    graph.add_edge("recommendation_agent", "response_agent")
    graph.add_edge("response_agent", END)

    return graph.compile()


def get_graph():
    """Lazily compile and cache the graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
        logger.info(
            "Agent graph ready (runtime=%s)", "langgraph" if _compiled_graph else "python-fallback"
        )
    return _compiled_graph


def _run_fallback(initial: AgentState) -> AgentState:
    """Plain-python execution of the same pipeline (no LangGraph needed)."""
    state: AgentState = dict(initial)  # type: ignore[assignment]
    for name, node in PIPELINE:
        state.update(node(state))  # type: ignore[typeddict-item]
        logger.debug("node %s finished", name)
    return state


def run_workflow(
    question: str = "",
    profile: Optional[UserProfile] = None,
    history: Optional[list] = None,
    mode: str = "chat",
    top_n: int = 5,
    scan_all: bool = False,
) -> AgentState:
    """
    Run the full multi-agent workflow and return the final state.

    Args:
        question:   the user's message.
        profile:    profile from the form, if the user filled it in.
        history:    previous chat turns (used as LLM context only).
        mode:       "chat" (question answering) or "recommend" (profile driven).
        top_n:      maximum number of schemes to return.
        scan_all:   evaluate the whole knowledge base instead of only the
                    retrieved schemes (used by /recommend).
    """
    initial = new_state(
        question=question,
        profile=profile,
        history=history or [],
        mode=mode,
        top_n=top_n,
        scan_all=scan_all,
    )

    graph = get_graph()
    if graph is None:
        return _run_fallback(initial)

    try:
        result = graph.invoke(initial)
        return result  # type: ignore[return-value]
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("LangGraph execution failed (%s). Using python fallback.", exc)
        return _run_fallback(initial)


def graph_summary() -> dict:
    """Small description of the workflow, served by /health for the UI."""
    return {
        "runtime": "langgraph" if LANGGRAPH_AVAILABLE else "python-fallback",
        "nodes": [name for name, _ in PIPELINE],
        "edges": [f"{PIPELINE[i][0]} -> {PIPELINE[i + 1][0]}" for i in range(len(PIPELINE) - 1)],
        "app": settings.app_name,
    }
