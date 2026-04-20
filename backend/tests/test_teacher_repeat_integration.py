"""Teacher repeat-question cache: same chat + same document scope skips LLM."""

import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage

from tests.test_api import _mock_chat_model_invoke, _mock_chat_model_stream, _mock_chunk_id, _mock_embed, client


def test_teacher_chat_reuses_answer_when_question_repeated_in_conversation() -> None:
    owner_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    owner_register = client.post("/auth/register", json=owner_payload)
    owner_headers = {"Authorization": f"Bearer {owner_register.json()['access_token']}"}
    mock_llm = _mock_chat_model_invoke("תשובה אחת")

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.vector_store.search", return_value=["Chunk context"]), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=mock_llm
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("repeat.txt", b"Repeat content.", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        first = client.post(
            "/teacher/chat",
            headers=owner_headers,
            json={"message": "  אותה שאלה  ", "document_ids": [doc_id]},
        )
        assert first.status_code == 200
        assert first.json().get("from_cache") is False
        conversation_id = first.json()["conversation_id"]
        second = client.post(
            "/teacher/chat",
            headers=owner_headers,
            json={"message": "אותה שאלה", "conversation_id": conversation_id, "document_ids": [doc_id]},
        )
        assert second.status_code == 200
        assert second.json().get("from_cache") is True
        assert second.json()["answer"] == "תשובה אחת"
    mock_llm.invoke.assert_called_once()


def test_teacher_chat_stream_skips_llm_on_repeat_question() -> None:
    owner_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    owner_register = client.post("/auth/register", json=owner_payload)
    owner_headers = {"Authorization": f"Bearer {owner_register.json()['access_token']}"}
    mock_stream_llm = _mock_chat_model_stream(["תשובה"])

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.vector_store.search", return_value=["Chunk context"]), patch(
        "app.agents.graphs.teacher.get_chat_model", return_value=mock_stream_llm
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("s.txt", b"S", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        r1 = client.post(
            "/teacher/chat/stream",
            headers=owner_headers,
            json={"message": "שאלה", "document_ids": [doc_id]},
        )
        assert r1.status_code == 200
        assert '"from_cache": false' in r1.text

        m = re.search(r'"conversation_id":\s*(\d+)', r1.text)
        assert m is not None
        cid = int(m.group(1))
        r2 = client.post(
            "/teacher/chat/stream",
            headers=owner_headers,
            json={"message": "שאלה", "conversation_id": cid, "document_ids": [doc_id]},
        )
        assert r2.status_code == 200
        assert '"from_cache": true' in r2.text
    mock_stream_llm.stream.assert_called_once()


def test_teacher_chat_does_not_reuse_when_document_scope_changes() -> None:
    owner_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    owner_register = client.post("/auth/register", json=owner_payload)
    owner_headers = {"Authorization": f"Bearer {owner_register.json()['access_token']}"}
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="מסמך א"),
        AIMessage(content="מסמך ב"),
    ]

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.vector_store.search", return_value=["Chunk context"]), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=mock_llm
    ):
        up_a = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("a.txt", b"A", "text/plain")},
        )
        up_b = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("b.txt", b"B", "text/plain")},
        )
        doc_a = up_a.json()["id"]
        doc_b = up_b.json()["id"]
        first = client.post(
            "/teacher/chat",
            headers=owner_headers,
            json={"message": "שאלה", "document_ids": [doc_a]},
        )
        assert first.status_code == 200
        cid = first.json()["conversation_id"]
        second = client.post(
            "/teacher/chat",
            headers=owner_headers,
            json={"message": "שאלה", "conversation_id": cid, "document_ids": [doc_b]},
        )
        assert second.status_code == 200
        assert second.json().get("from_cache") is False
    assert mock_llm.invoke.call_count == 2


def test_teacher_repeat_cache_helpers() -> None:
    from app.services.teacher_repeat_cache import document_scope_json, normalize_teacher_message

    assert normalize_teacher_message("  x  \n y ") == "x y"
    assert document_scope_json([2, 1]) == "[1, 2]"
