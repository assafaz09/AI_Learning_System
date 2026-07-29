"""Group learning API: alternating peer agents."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage

from tests.test_api import _mock_chunk_id, _mock_embed, client


def test_group_learning_alternates_speakers_and_persists_messages() -> None:
    payload = {"email": f"gl-{uuid4()}@example.com", "password": "Secret123"}
    reg = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="תגובת מתחיל"),
        AIMessage(content="תגובת בינוני"),
    ]

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_group_learning.vector_store.search", return_value=["קטע א", "קטע ב"]), patch(
        "app.services.group_peer_chat.get_chat_model", return_value=mock_llm
    ):
        up = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("g.txt", b"group doc", "text/plain")},
        )
        assert up.status_code == 200
        doc_id = up.json()["id"]

        sess = client.post(
            "/group-learning/sessions",
            headers=headers,
            json={"document_ids": [doc_id], "title": "סשן בדיקה"},
        )
        assert sess.status_code == 200
        sid = sess.json()["id"]
        assert sess.json()["next_speaker"] == "novice"

        m1 = client.post(
            "/group-learning/sessions/{}/message".format(sid),
            headers=headers,
            json={"message": "אסביר את הנושא"},
        )
        assert m1.status_code == 200
        assert m1.json()["speaker"] == "novice"
        assert m1.json()["reply"] == "תגובת מתחיל"

        listed = client.get("/group-learning/sessions", headers=headers)
        assert listed.status_code == 200
        row = next(x for x in listed.json() if x["id"] == sid)
        assert row["next_speaker"] == "intermediate"

        m2 = client.post(
            "/group-learning/sessions/{}/message".format(sid),
            headers=headers,
            json={"message": "המשך הסבר"},
        )
        assert m2.status_code == 200
        assert m2.json()["speaker"] == "intermediate"
        assert m2.json()["reply"] == "תגובת בינוני"

    assert mock_llm.invoke.call_count == 2

    msgs = client.get(f"/group-learning/sessions/{sid}/messages", headers=headers)
    assert msgs.status_code == 200
    body = msgs.json()
    assert len(body["messages"]) == 4
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "novice", "user", "intermediate"]


def test_group_learning_fails_without_retrieval_context() -> None:
    payload = {"email": f"gl2-{uuid4()}@example.com", "password": "Secret123"}
    reg = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    mock_llm = MagicMock()

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_group_learning.vector_store.search", return_value=[]), patch(
        "app.services.group_peer_chat.get_chat_model", return_value=mock_llm
    ):
        up = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("empty.txt", b"x", "text/plain")},
        )
        doc_id = up.json()["id"]
        sess = client.post("/group-learning/sessions", headers=headers, json={"document_ids": [doc_id]})
        sid = sess.json()["id"]
        m1 = client.post(
            "/group-learning/sessions/{}/message".format(sid),
            headers=headers,
            json={"message": "שלום"},
        )
        assert m1.status_code == 409
    mock_llm.invoke.assert_not_called()


def test_group_learning_session_requires_valid_documents() -> None:
    payload = {"email": f"gl3-{uuid4()}@example.com", "password": "Secret123"}
    reg = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    bad = client.post("/group-learning/sessions", headers=headers, json={"document_ids": [99999]})
    assert bad.status_code == 400
