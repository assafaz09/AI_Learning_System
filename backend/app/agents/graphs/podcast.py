from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.nodes.llm_nodes import podcast_script_llm
from app.agents.nodes.podcast_nodes import podcast_parse_script
from app.agents.nodes.routing import route_podcast_parse
from app.agents.state import AgentGraphState

_cached_podcast_script: object | None = None


def _compiled_podcast_script():
    global _cached_podcast_script
    if _cached_podcast_script is None:
        _cached_podcast_script = _build_podcast_script_graph()
    return _cached_podcast_script


def _build_podcast_script_graph():
    graph = StateGraph(AgentGraphState)
    graph.add_node("generate", podcast_script_llm)
    graph.add_node("parse", podcast_parse_script)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "parse")
    graph.add_conditional_edges(
        "parse",
        route_podcast_parse,
        {"tts_ready": END, "retry_script": "generate", "script_failed": END},
    )
    return graph.compile()


def invoke_podcast_script_pipeline(
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    return _compiled_podcast_script().invoke(state, config=config)
