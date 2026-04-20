from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.nodes.llm_nodes import open_question_grade_llm, quiz_generation_llm
from app.agents.nodes.quiz_nodes import quiz_parse_and_validate
from app.agents.nodes.routing import route_quiz_generation
from app.agents.state import AgentGraphState

_cached_quiz_generate: object | None = None
_cached_open_grade: object | None = None


def _compiled_quiz_generate():
    global _cached_quiz_generate
    if _cached_quiz_generate is None:
        _cached_quiz_generate = _build_quiz_generate_graph()
    return _cached_quiz_generate


def _compiled_open_grade():
    global _cached_open_grade
    if _cached_open_grade is None:
        _cached_open_grade = _build_open_grade_graph()
    return _cached_open_grade


def _apply_quiz_fallback_material(state: AgentGraphState) -> dict:
    return {
        "joined_doc_excerpt": "חומר כללי: עברו על הנושא, הגדירו מושגים מרכזיים, ותרגלו דוגמאות קצרות.",
    }


def _build_quiz_generate_graph():
    graph = StateGraph(AgentGraphState)
    graph.add_node("gate", lambda s: {})
    graph.add_node("fallback_material", _apply_quiz_fallback_material)
    graph.add_node("generate", quiz_generation_llm)
    graph.add_node("validate", quiz_parse_and_validate)

    graph.set_entry_point("gate")
    graph.add_conditional_edges(
        "gate",
        route_quiz_generation,
        {"llm_generate_quiz": "generate", "use_fallback_prompt": "fallback_material"},
    )
    graph.add_edge("fallback_material", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


def invoke_quiz_generate(
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    return _compiled_quiz_generate().invoke(state, config=config)


def _build_open_grade_graph():
    graph = StateGraph(AgentGraphState)
    graph.add_node("grade", open_question_grade_llm)
    graph.set_entry_point("grade")
    graph.add_edge("grade", END)
    return graph.compile()


def invoke_open_grade(
    state: AgentGraphState,
    *,
    config: RunnableConfig | None = None,
) -> AgentGraphState:
    return _compiled_open_grade().invoke(state, config=config)
