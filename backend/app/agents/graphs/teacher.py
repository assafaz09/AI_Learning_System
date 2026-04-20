from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.llm import get_chat_model
from app.agents.nodes.llm_nodes import project_ideas_llm_reply, teacher_llm_reply
from app.agents.nodes.retrieval import project_ideas_retrieve_and_prompt, teacher_retrieve_and_prompt
from app.agents.nodes.routing import route_after_teacher_retrieval
from app.agents.state import AgentGraphState
from app.prompts import TEACHER_SYSTEM_PROMPT
from app.services.vector_store import VectorStore

_cached_vs_id: int | None = None
_cached_teacher_chat: object | None = None
_cached_project_ideas: object | None = None


def _compiled_teacher_pair(vector_store: VectorStore) -> tuple[object, object]:
    """Reuse compiled graphs per VectorStore instance (avoid compile on every request)."""
    global _cached_vs_id, _cached_teacher_chat, _cached_project_ideas
    vid = id(vector_store)
    if _cached_vs_id != vid:
        _cached_vs_id = vid
        _cached_teacher_chat = _build_teacher_chat_graph(vector_store)
        _cached_project_ideas = _build_project_ideas_graph(vector_store)
    assert _cached_teacher_chat is not None and _cached_project_ideas is not None
    return _cached_teacher_chat, _cached_project_ideas


def _build_teacher_chat_graph(vector_store: VectorStore):
    graph = StateGraph(AgentGraphState)

    graph.add_node("retrieve", lambda s: teacher_retrieve_and_prompt(s, vector_store))
    graph.add_node("reply", teacher_llm_reply)

    graph.set_entry_point("retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_after_teacher_retrieval,
        {"build_teacher_prompt": "reply", "no_context": END},
    )
    graph.add_edge("reply", END)
    return graph.compile()


def _build_project_ideas_graph(vector_store: VectorStore):
    graph = StateGraph(AgentGraphState)

    graph.add_node("retrieve", lambda s: project_ideas_retrieve_and_prompt(s, vector_store))
    graph.add_node("reply", project_ideas_llm_reply)

    graph.set_entry_point("retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_after_teacher_retrieval,
        {"build_teacher_prompt": "reply", "no_context": END},
    )
    graph.add_edge("reply", END)
    return graph.compile()


def invoke_teacher_chat(
    vector_store: VectorStore,
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    app, _ = _compiled_teacher_pair(vector_store)
    return app.invoke(state, config=config)


def invoke_project_ideas(
    vector_store: VectorStore,
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    _, app = _compiled_teacher_pair(vector_store)
    return app.invoke(state, config=config)


def teacher_retrieval_phase(
    vector_store: VectorStore,
    *,
    user_id: int,
    document_ids: list[int],
    message: str,
) -> AgentGraphState:
    """Run retrieval + prompt build (used for streaming chat before token stream)."""
    initial: AgentGraphState = {"user_id": user_id, "document_ids": document_ids, "user_message": message}
    merged = {**initial, **teacher_retrieve_and_prompt(initial, vector_store)}
    route = route_after_teacher_retrieval(merged)
    if route == "no_context":
        return merged
    return merged


def iter_teacher_reply_stream(state: AgentGraphState) -> Iterator[str]:
    user_prompt = state.get("teacher_user_prompt") or ""
    llm = get_chat_model(streaming=True)
    for chunk in llm.stream([SystemMessage(content=TEACHER_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]):
        content: Any = getattr(chunk, "content", None)
        if isinstance(content, str) and content:
            yield content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    t = part.get("text")
                    if t:
                        yield str(t)
