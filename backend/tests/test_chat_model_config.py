"""Per-task chat model resolution (cost routing)."""

from unittest.mock import MagicMock, patch

from app.core.config import Settings


def test_resolve_chat_model_falls_back_when_task_override_empty() -> None:
    s = Settings(
        openai_chat_model="gpt-4o-mini",
        openai_model_teacher="",
        openai_model_quiz_generate="",
    )
    assert s.resolve_chat_model("teacher") == "gpt-4o-mini"
    assert s.resolve_chat_model("quiz_generate") == "gpt-4o-mini"
    assert s.resolve_chat_model("default") == "gpt-4o-mini"


def test_resolve_chat_model_uses_explicit_overrides() -> None:
    s = Settings(
        openai_chat_model="gpt-4o-mini",
        openai_model_teacher="gpt-4o",
        openai_model_project_ideas="gpt-4o-mini",
        openai_model_quiz_generate="gpt-4o-mini",
        openai_model_quiz_grade="gpt-4o",
        openai_model_podcast="gpt-4o-mini",
    )
    assert s.resolve_chat_model("teacher") == "gpt-4o"
    assert s.resolve_chat_model("project_ideas") == "gpt-4o-mini"
    assert s.resolve_chat_model("quiz_grade") == "gpt-4o"
    assert s.resolve_chat_model("podcast") == "gpt-4o-mini"


def test_get_chat_model_passes_resolved_name_to_chat_openai() -> None:
    with patch("app.agents.llm.ChatOpenAI") as mock_cls:
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-x"
        mock_settings.resolve_chat_model = MagicMock(side_effect=lambda t: f"model-for-{t}")
        with patch("app.agents.llm.settings", mock_settings):
            from app.agents.llm import get_chat_model

            get_chat_model(task="quiz_grade", streaming=False, temperature=0.1)
    mock_settings.resolve_chat_model.assert_called_once_with("quiz_grade")
    mock_cls.assert_called_once()
    kwargs = mock_cls.call_args.kwargs
    assert kwargs["model"] == "model-for-quiz_grade"
    assert kwargs["temperature"] == 0.1
    assert kwargs["streaming"] is False


def test_ai_client_chat_uses_resolve_chat_model() -> None:
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.resolve_chat_model = MagicMock(return_value="resolved-m")
        from app.services.ai import AIClient

        ai = AIClient()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="hi"))]
        ai.client.chat.completions.create = MagicMock(return_value=mock_resp)
        out = ai.chat("sys", "user", task="podcast")
        assert out == "hi"
        ai.client.chat.completions.create.assert_called_once()
        assert ai.client.chat.completions.create.call_args.kwargs["model"] == "resolved-m"
        mock_settings.resolve_chat_model.assert_called_once_with("podcast")
