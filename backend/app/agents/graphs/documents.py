from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.nodes.indexing import index_document_content
from app.agents.state import AgentGraphState
from app.services.vector_store import VectorStore

_cached_index_vs_id: int | None = None
_cached_index: object | None = None


def _compiled_index(vector_store: VectorStore):
    global _cached_index_vs_id, _cached_index
    vid = id(vector_store)
    if _cached_index_vs_id != vid:
        _cached_index_vs_id = vid
        _cached_index = _build_index_graph(vector_store)
    assert _cached_index is not None
    return _cached_index


def _build_index_graph(vector_store: VectorStore):
    graph = StateGraph(AgentGraphState)
    graph.add_node("index", lambda s: index_document_content(s, vector_store))
    graph.set_entry_point("index")
    graph.add_edge("index", END)
    return graph.compile()


def invoke_document_index(
    vector_store: VectorStore,
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    return _compiled_index(vector_store).invoke(state, config=config)
