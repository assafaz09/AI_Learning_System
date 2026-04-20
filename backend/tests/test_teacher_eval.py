"""Teacher agent eval harness: dataset + stub retrieval (no Qdrant)."""

from unittest.mock import MagicMock, patch

from eval.teacher_eval import (
    StubTeacherVectorStore,
    load_teacher_cases,
    run_teacher_case,
    summarize_teacher_result,
)


def test_load_teacher_cases_minimum_size() -> None:
    cases = load_teacher_cases()
    assert len(cases) >= 2
    ids = {c.id for c in cases}
    assert "photosynthesis-light" in ids
    assert "no-retrieval" in ids


def test_stub_vector_store_returns_limited_chunks() -> None:
    vs = StubTeacherVectorStore(["a", "b", "c"])
    assert vs.search([], 1, [1], limit=2) == ["a", "b"]


@patch("app.agents.nodes.llm_nodes.get_chat_model")
def test_teacher_eval_runs_llm_when_context_exists(mock_get_chat: MagicMock) -> None:
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="תשובה מסכמת את תפקיד האור.")
    mock_get_chat.return_value = mock_llm
    with patch("app.agents.nodes.retrieval.ai_client.embed", return_value=[0.0] * 1536):
        cases = load_teacher_cases()
        case = next(c for c in cases if c.id == "photosynthesis-light")
        out = run_teacher_case(case)
    mock_get_chat.assert_called_once()
    assert "תשובה מסכמת" in (out.get("llm_output") or "")
    assert len(out.get("retrieved_chunks") or []) == 2


@patch("app.agents.nodes.llm_nodes.get_chat_model")
def test_teacher_eval_skips_llm_without_context(mock_get_chat: MagicMock) -> None:
    with patch("app.agents.nodes.retrieval.ai_client.embed", return_value=[0.0] * 1536):
        cases = load_teacher_cases()
        case = next(c for c in cases if c.id == "no-retrieval")
        out = run_teacher_case(case)
    mock_get_chat.assert_not_called()
    assert not (out.get("llm_output") or "").strip()
    assert out.get("error_detail")


def test_summarize_teacher_result_shape() -> None:
    summary = summarize_teacher_result(
        "x",
        {"llm_output": "abc" * 100, "retrieved_chunks": ["a"], "error_detail": ""},
    )
    assert summary["case_id"] == "x"
    assert summary["has_llm_output"] is True
    assert summary["retrieved_n"] == 1
    assert "…" in summary["llm_preview"]
