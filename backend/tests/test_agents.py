"""Unit tests for LangGraph routing and agent helpers (no DB)."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.nodes import llm_nodes
from app.agents.nodes.routing import route_after_teacher_retrieval, route_quiz_generation
from app.agents.quiz_utils import normalize_question_type, validate_generated_questions
from app.agents.state import AgentGraphState


def test_route_after_teacher_retrieval_no_context_on_error():
    state: AgentGraphState = {"error_detail": "missing", "retrieved_chunks": ["x"]}
    assert route_after_teacher_retrieval(state) == "no_context"


def test_route_after_teacher_retrieval_no_context_empty_chunks():
    state: AgentGraphState = {"retrieved_chunks": [], "error_detail": ""}
    assert route_after_teacher_retrieval(state) == "no_context"


def test_route_after_teacher_retrieval_build_prompt():
    state: AgentGraphState = {"retrieved_chunks": ["a"], "error_detail": ""}
    assert route_after_teacher_retrieval(state) == "build_teacher_prompt"


def test_route_quiz_generation_fallback_when_short_material():
    state: AgentGraphState = {"joined_doc_excerpt": "short"}
    assert route_quiz_generation(state) == "use_fallback_prompt"


def test_route_quiz_generation_llm_when_enough_material():
    state: AgentGraphState = {"joined_doc_excerpt": "x" * 30}
    assert route_quiz_generation(state) == "llm_generate_quiz"


def test_normalize_question_type_mcq_aliases():
    assert normalize_question_type("אמריקאית") == "mcq"
    assert normalize_question_type("open") == "open"


def test_validate_generated_questions_filters_invalid_mcq():
    items = [
        {
            "prompt": "Q1",
            "type": "mcq",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "a",
            "reference_answer": "",
        }
    ]
    out = validate_generated_questions(items, "mcq", 1)
    assert len(out) == 1
    assert out[0]["correct_answer"] == "a"


def test_open_question_grade_llm_heuristic_fallback():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="not json")
    with patch.object(llm_nodes, "get_chat_model", return_value=mock_llm):
        out = llm_nodes.open_question_grade_llm(
            {
                "question_prompt": "מה זה X?",
                "reference_answer": "הגדרה אחת שנייה",
                "user_answer": "הגדרה אחת",
            }
        )
    assert out["grade_score"] >= 0
    assert "llm_grade_parse_failed" in (out.get("errors") or [])


def test_quiz_compiled_graphs_are_singletons():
    from app.agents.graphs import quiz as qz

    qz._cached_quiz_generate = None
    qz._cached_open_grade = None
    gen_a = qz._compiled_quiz_generate()
    gen_b = qz._compiled_quiz_generate()
    assert gen_a is gen_b
    grade_a = qz._compiled_open_grade()
    grade_b = qz._compiled_open_grade()
    assert grade_a is grade_b


def test_podcast_compiled_graph_singleton():
    from app.agents.graphs import podcast as pc

    pc._cached_podcast_script = None
    a = pc._compiled_podcast_script()
    b = pc._compiled_podcast_script()
    assert a is b


def test_documents_index_graph_reuses_per_vector_store_instance():
    from app.agents.graphs import documents as doc

    vs = MagicMock()
    doc._cached_index_vs_id = None
    doc._cached_index = None
    a = doc._compiled_index(vs)
    b = doc._compiled_index(vs)
    assert a is b
    vs2 = MagicMock()
    c = doc._compiled_index(vs2)
    assert c is not a


def test_teacher_graphs_reuse_per_vector_store_instance():
    from app.agents.graphs import teacher as tch

    vs = MagicMock()
    tch._cached_vs_id = None
    tch._cached_teacher_chat = None
    tch._cached_project_ideas = None
    ta, pa = tch._compiled_teacher_pair(vs)
    tb, pb = tch._compiled_teacher_pair(vs)
    assert ta is tb and pa is pb
    vs2 = MagicMock()
    ta2, _ = tch._compiled_teacher_pair(vs2)
    assert ta2 is not ta
