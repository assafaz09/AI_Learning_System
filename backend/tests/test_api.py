import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test.db'}"
os.environ["QDRANT_URL"] = "http://invalid-qdrant:6333"
os.environ["OPENAI_API_KEY"] = ""

from app.main import app  # noqa: E402


client = TestClient(app)


def _mock_embed(_: str) -> list[float]:
    return [0.1] * 64


def _mock_chunk_id() -> str:
    return str(uuid4())


def _mock_chat_model_invoke(content: str) -> MagicMock:
    from langchain_core.messages import AIMessage

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=content)
    return mock_llm


def _mock_chat_model_stream(parts: list[str]) -> MagicMock:
    mock_llm = MagicMock()

    class _Chunk:
        __slots__ = ("content",)

        def __init__(self, c: str):
            self.content = c

    mock_llm.stream.return_value = iter([_Chunk(p) for p in parts])
    return mock_llm


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    assert register.status_code == 200
    assert "access_token" in register.json()
    assert register.json().get("refresh_token") is None
    assert "refresh_token=" in (register.headers.get("set-cookie") or "")

    login = client.post("/auth/login", json=payload)
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert "refresh_token=" in (login.headers.get("set-cookie") or "")

    refreshed = client.post("/auth/refresh", json={})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()


def test_selected_documents_flow():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        first_doc = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("doc1.txt", b"First text document for testing.", "text/plain")},
        )
        second_doc = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("doc2.txt", b"Second text document for testing.", "text/plain")},
        )
    assert first_doc.status_code == 200
    assert second_doc.status_code == 200

    doc_ids = [first_doc.json()["id"], second_doc.json()["id"]]
    save_selected = client.put("/documents/selected", headers=headers, json={"document_ids": doc_ids})
    assert save_selected.status_code == 200
    assert sorted(save_selected.json()["document_ids"]) == sorted(doc_ids)

    get_selected = client.get("/documents/selected", headers=headers)
    assert get_selected.status_code == 200
    assert sorted(get_selected.json()["document_ids"]) == sorted(doc_ids)


def test_pdf_upload_uses_pdf_parser():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_reader = Mock()
    fake_page = Mock()
    fake_page.extract_text.return_value = "This is text extracted from PDF."
    fake_reader.pages = [fake_page]

    with patch("app.api.routes_documents.PdfReader", return_value=fake_reader), patch(
        "app.api.routes_documents.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id), patch(
        "app.api.routes_documents.vector_store.upsert_chunk", return_value=None
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )
    assert uploaded.status_code == 200
    assert uploaded.json()["name"] == "study.pdf"


def test_reindex_documents():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("doc.txt", b"Reindex source content.", "text/plain")},
        )
        assert uploaded.status_code == 200
        reindex = client.post("/documents/reindex", headers=headers)

    assert reindex.status_code == 200
    assert reindex.json()["documents"] == 1
    assert reindex.json()["chunks"] >= 1


def test_delete_document_removes_selection():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("delete-me.txt", b"delete me", "text/plain")},
        )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]

    selected = client.put("/documents/selected", headers=headers, json={"document_ids": [doc_id]})
    assert selected.status_code == 200
    assert selected.json()["document_ids"] == [doc_id]

    deleted = client.delete(f"/documents/{doc_id}", headers=headers)
    assert deleted.status_code == 204

    docs = client.get("/documents", headers=headers)
    assert docs.status_code == 200
    assert all(item["id"] != doc_id for item in docs.json())

    selected_after = client.get("/documents/selected", headers=headers)
    assert selected_after.status_code == 200
    assert selected_after.json()["document_ids"] == []


def test_conversation_messages_requires_ownership_and_keeps_order():
    owner_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    owner_register = client.post("/auth/register", json=owner_payload)
    owner_headers = {"Authorization": f"Bearer {owner_register.json()['access_token']}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch(
        "app.api.routes_teacher.vector_store.search", return_value=["Chunk context"]
    ), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=_mock_chat_model_invoke("תשובה ראשונה")
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("order.txt", b"Order content.", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        selected = client.put("/documents/selected", headers=owner_headers, json={"document_ids": [doc_id]})
        assert selected.status_code == 200
        chat = client.post(
            "/teacher/chat",
            headers=owner_headers,
            json={"message": "first question", "document_ids": [doc_id]},
        )
        assert chat.status_code == 200

    conversation_id = chat.json()["conversation_id"]
    messages = client.get(f"/teacher/conversations/{conversation_id}/messages", headers=owner_headers)
    assert messages.status_code == 200
    body = messages.json()
    assert body["conversation_id"] == conversation_id
    assert [item["role"] for item in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "first question"
    assert body["messages"][1]["content"] == "תשובה ראשונה"

    other_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    other_register = client.post("/auth/register", json=other_payload)
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}
    unauthorized = client.get(f"/teacher/conversations/{conversation_id}/messages", headers=other_headers)
    assert unauthorized.status_code == 404


def test_delete_document_requires_ownership():
    owner_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    owner_register = client.post("/auth/register", json=owner_payload)
    owner_headers = {"Authorization": f"Bearer {owner_register.json()['access_token']}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        uploaded = client.post(
            "/documents/upload",
            headers=owner_headers,
            files={"file": ("private.txt", b"private", "text/plain")},
        )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]

    other_payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    other_register = client.post("/auth/register", json=other_payload)
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    delete_attempt = client.delete(f"/documents/{doc_id}", headers=other_headers)
    assert delete_attempt.status_code == 404

    owner_docs = client.get("/documents", headers=owner_headers)
    assert owner_docs.status_code == 200
    assert any(item["id"] == doc_id for item in owner_docs.json())


def test_teacher_chat_stream_returns_deltas_and_persists_messages():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.vector_store.search", return_value=["Chunk context"]), patch(
        "app.agents.graphs.teacher.get_chat_model", return_value=_mock_chat_model_stream(["שלום", " עולם"])
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("stream.txt", b"Streaming content.", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        selected = client.put("/documents/selected", headers=headers, json={"document_ids": [doc_id]})
        assert selected.status_code == 200

        stream_response = client.post(
            "/teacher/chat/stream",
            headers=headers,
            json={"message": "מה למדת?", "document_ids": [doc_id]},
        )

    assert stream_response.status_code == 200
    body = stream_response.text
    assert "event: delta" in body
    assert '"delta": "שלום"' in body
    assert '"delta": " עולם"' in body
    assert "event: done" in body

    match = re.search(r'"conversation_id":\s*(\d+)', body)
    assert match is not None
    conversation_id = int(match.group(1))
    messages = client.get(f"/teacher/conversations/{conversation_id}/messages", headers=headers)
    assert messages.status_code == 200
    roles = [item["role"] for item in messages.json()["messages"]]
    assert "user" in roles
    assert "assistant" in roles


def test_teacher_project_ideas_returns_suggestions():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.services.ai.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.vector_store.search", return_value=["Context chunk"]), patch(
        "app.agents.nodes.llm_nodes.get_chat_model",
        return_value=_mock_chat_model_invoke("1. פרויקט לדוגמה\nתיאור קצר."),
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("proj.txt", b"content", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        selected = client.put("/documents/selected", headers=headers, json={"document_ids": [doc_id]})
        assert selected.status_code == 200

        res = client.post(
            "/teacher/project-ideas",
            headers=headers,
            json={
                "learning_focus": "להבין את הנושא לעומק",
                "experience_band": "beginner_short",
                "document_ids": [doc_id],
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert "suggestions" in data
    assert "פרויקט" in data["suggestions"]


def test_saved_projects_crud():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    empty = client.get("/teacher/saved-projects", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    create = client.post(
        "/teacher/saved-projects",
        headers=headers,
        json={
            "kind": "ai",
            "title": "פרויקט ראשון",
            "suggestions_body": "## רעיון\nתיאור",
            "learning_focus": "פייתון",
            "experience_band": "beginner_short",
            "document_ids": [1, 2],
        },
    )
    assert create.status_code == 200
    created = create.json()
    assert created["title"] == "פרויקט ראשון"
    assert created["kind"] == "ai"
    assert created["importance"] == "medium"
    assert created["status"] == "not_started"
    assert created["document_ids"] == [1, 2]
    project_id = created["id"]

    listed = client.get("/teacher/saved-projects", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == project_id

    patched = client.patch(
        f"/teacher/saved-projects/{project_id}",
        headers=headers,
        json={"status": "in_progress", "notes": "מתחילים השבוע"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_progress"
    assert patched.json()["notes"] == "מתחילים השבוע"

    deleted = client.delete(f"/teacher/saved-projects/{project_id}", headers=headers)
    assert deleted.status_code == 204

    after = client.get("/teacher/saved-projects", headers=headers)
    assert after.json() == []

    missing = client.patch(f"/teacher/saved-projects/{project_id}", headers=headers, json={"status": "done"})
    assert missing.status_code == 404


def test_saved_projects_manual_create():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    create = client.post(
        "/teacher/saved-projects",
        headers=headers,
        json={
            "kind": "manual",
            "title": "ללמוד Rust",
            "description": "לעבור על ספר בסיסי ולכתוב CLI קטן",
            "importance": "high",
            "status": "in_progress",
        },
    )
    assert create.status_code == 200
    data = create.json()
    assert data["kind"] == "manual"
    assert data["importance"] == "high"
    assert data["status"] == "in_progress"
    assert data["description"] == "לעבור על ספר בסיסי ולכתוב CLI קטן"
    assert data["document_ids"] == []
    assert data["experience_band"] == "manual"


def test_submit_quiz_returns_detailed_feedback_text():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    generated_payload = {
        "questions": [
            {
                "prompt": "מהי למידת מכונה?",
                "type": "open",
                "reference_answer": "למידת מכונה היא שיטה שבה מודל לומד מתבניות בנתונים.",
                "explanation": "התייחס/י להגדרה ולרעיון הלמידה מנתונים.",
            }
        ]
    }
    semantic_eval_payload = {
        "score_0_to_100": 86,
        "why": "התשובה שלך נכונה רעיונית גם אם הניסוח שונה.",
        "how_to_improve": "הוסף/י דוגמה קצרה לאופן שבו מודל לומד מנתונים.",
        "accepted_semantically": True,
    }

    from langchain_core.messages import AIMessage

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content=json.dumps(generated_payload, ensure_ascii=False)),
        AIMessage(content=json.dumps(semantic_eval_payload, ensure_ascii=False)),
    ]
    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=mock_llm
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("quiz-feedback.txt", b"ML content", "text/plain")},
        )
        assert uploaded.status_code == 200
        doc_id = uploaded.json()["id"]
        generated = client.post(
            "/quiz/generate",
            headers=headers,
            json={"document_ids": [doc_id], "difficulty": "medium", "question_count": 1, "question_type": "open"},
        )
        assert generated.status_code == 200
        quiz_id = generated.json()["id"]
        question_id = generated.json()["questions"][0]["id"]

        submitted = client.post(
            f"/quiz/{quiz_id}/submit",
            headers=headers,
            json={"answers": {str(question_id): "מודל שלומד ממידע קיים ומשפר ביצועים עם הזמן."}},
        )
    assert submitted.status_code == 200
    body = submitted.json()
    assert "feedback_items" in body
    assert body["feedback_items"][0]["accepted_semantically"] is True
    assert body["feedback_items"][0]["why"]
    assert body["feedback_items"][0]["how_to_improve"]


def test_generate_quiz_requires_question_type():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("quiz-type-source.txt", b"source", "text/plain")},
        )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]

    response = client.post(
        "/quiz/generate",
        headers=headers,
        json={"document_ids": [doc_id], "difficulty": "medium", "question_count": 1},
    )
    assert response.status_code == 422


def test_import_external_web_source():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    fake_response = Mock()
    fake_response.text = (
        "<html><head><title>AI Article</title></head><body>"
        "<h1>Machine Learning</h1><p>Models learn patterns from data.</p></body></html>"
    )
    fake_response.raise_for_status = Mock()

    with patch("app.api.routes_documents.get", return_value=fake_response), patch(
        "app.api.routes_documents.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id), patch(
        "app.api.routes_documents.vector_store.upsert_chunk", return_value=None
    ):
        imported = client.post("/documents/import-url", headers=headers, json={"url": "https://example.com/article"})

    assert imported.status_code == 200
    assert imported.json()["name"] == "AI Article"
    assert imported.json()["source_type"] == "web"
    assert imported.json()["source_url"] == "https://example.com/article"
    assert imported.json()["external_id"] is None


def test_import_external_youtube_source():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    with patch(
        "app.api.routes_documents.YouTubeTranscriptApi.get_transcript",
        return_value=[{"text": "line one"}, {"text": "line two"}],
    ), patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        imported = client.post(
            "/documents/import-url",
            headers=headers,
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

    assert imported.status_code == 200
    assert imported.json()["name"] == "YouTube:dQw4w9WgXcQ"
    assert imported.json()["source_type"] == "youtube"
    assert imported.json()["external_id"] == "dQw4w9WgXcQ"


def test_import_external_youtube_without_transcript_uses_audio_transcription():
    payload = {"email": f"user-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    with patch(
        "app.api.routes_documents.YouTubeTranscriptApi.get_transcript",
        side_effect=Exception("no transcript"),
    ), patch(
        "app.api.routes_documents._download_youtube_audio",
        return_value=Path("/tmp/fake-audio.mp3"),
    ), patch(
        "app.api.routes_documents.ai_client.transcribe_audio",
        return_value="transcribed audio content",
    ), patch(
        "app.api.routes_documents.ai_client.embed", side_effect=_mock_embed
    ), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None
    ):
        imported = client.post(
            "/documents/import-url",
            headers=headers,
            json={"url": "https://www.youtube.com/watch?v=abc123xyz99"},
        )

    assert imported.status_code == 200
    assert imported.json()["source_type"] == "youtube"
    assert imported.json()["external_id"] == "abc123xyz99"


def test_teacher_prompt_contains_pedagogical_instructions():
    from app.prompts.teacher import TEACHER_SYSTEM_PROMPT, build_teacher_user_prompt

    assert "הבנה לפני שינון" in TEACHER_SYSTEM_PROMPT
    assert "אל תמציא מידע" in TEACHER_SYSTEM_PROMPT
    assert "אנלוגיות" in TEACHER_SYSTEM_PROMPT
    assert "הקשר" in TEACHER_SYSTEM_PROMPT
    assert len(TEACHER_SYSTEM_PROMPT) > 500

    prompt = build_teacher_user_prompt("מה זה ML?", ["ML is machine learning.", "It learns from data."])
    assert "ML is machine learning." in prompt
    assert "It learns from data." in prompt
    assert "מה זה ML?" in prompt
    assert "---" in prompt


def test_quiz_prompt_contains_format_and_quality_rules():
    from app.prompts.quiz import QUIZ_GENERATOR_SYSTEM_PROMPT, build_quiz_generation_prompt

    assert "JSON תקין בלבד" in QUIZ_GENERATOR_SYSTEM_PROMPT
    assert "4 אפשרויות" in QUIZ_GENERATOR_SYSTEM_PROMPT
    assert "correct_answer" in QUIZ_GENERATOR_SYSTEM_PROMPT
    assert "reference_answer" in QUIZ_GENERATOR_SYSTEM_PROMPT
    assert "בקרת איכות" in QUIZ_GENERATOR_SYSTEM_PROMPT
    assert len(QUIZ_GENERATOR_SYSTEM_PROMPT) > 500

    mcq_prompt = build_quiz_generation_prompt("mcq", 5, "medium", "some material")
    assert "5" in mcq_prompt
    assert "בינוני" in mcq_prompt
    assert "some material" in mcq_prompt

    open_prompt = build_quiz_generation_prompt("open", 3, "hard", "other material")
    assert "3" in open_prompt
    assert "קשה" in open_prompt


def test_grading_prompt_contains_evaluation_criteria():
    from app.prompts.grading import QUIZ_GRADER_SYSTEM_PROMPT, build_semantic_grading_prompt

    assert "סמנטית" in QUIZ_GRADER_SYSTEM_PROMPT
    assert "90-100" in QUIZ_GRADER_SYSTEM_PROMPT
    assert "0-24" in QUIZ_GRADER_SYSTEM_PROMPT
    assert "accepted_semantically" in QUIZ_GRADER_SYSTEM_PROMPT
    assert "how_to_improve" in QUIZ_GRADER_SYSTEM_PROMPT
    assert len(QUIZ_GRADER_SYSTEM_PROMPT) > 500

    prompt = build_semantic_grading_prompt("מה זה AI?", "בינה מלאכותית", "זה מחשב חכם")
    assert "מה זה AI?" in prompt
    assert "בינה מלאכותית" in prompt
    assert "זה מחשב חכם" in prompt

    empty_prompt = build_semantic_grading_prompt("שאלה", "תשובה", "")
    assert "לא ניתנה תשובה" in empty_prompt


def test_podcast_prompt_contains_dialogue_instructions():
    from app.prompts.podcast import PODCAST_SYSTEM_PROMPT, build_podcast_user_prompt

    assert "דני" in PODCAST_SYSTEM_PROMPT
    assert "מיכל" in PODCAST_SYSTEM_PROMPT
    assert "speaker" in PODCAST_SYSTEM_PROMPT
    assert "JSON" in PODCAST_SYSTEM_PROMPT
    assert len(PODCAST_SYSTEM_PROMPT) > 300

    prompt = build_podcast_user_prompt("חומר לימוד על מתמטיקה")
    assert "חומר לימוד על מתמטיקה" in prompt
    assert "40-60" in prompt


def test_text_to_speech_calls_openai():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_tts_model = "tts-1"

        from app.services.ai import AIClient

        ai = AIClient()
        mock_response = MagicMock()
        mock_response.content = b"fake-mp3-bytes"
        ai.client.audio.speech.create = MagicMock(return_value=mock_response)

        result = ai.text_to_speech("שלום עולם", voice="alloy")
        assert result == b"fake-mp3-bytes"
        ai.client.audio.speech.create.assert_called_once_with(
            model="tts-1", voice="alloy", input="שלום עולם", response_format="mp3"
        )


def test_podcast_list_empty_for_new_user():
    payload = {"email": f"user-podcast-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/podcast/list", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_podcast_generate_requires_documents():
    payload = {"email": f"user-podcast-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/podcast/generate", json={"document_ids": []}, headers=headers)
    assert response.status_code == 400


def test_podcast_audio_not_found_for_invalid_id():
    payload = {"email": f"user-podcast-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/podcast/99999/audio", headers=headers)
    assert response.status_code == 404


def test_transcribe_audio_uses_local_whisper_when_configured():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.whisper_mode = "local"
        mock_settings.whisper_local_model = "base"

        from app.services.ai import AIClient

        ai = AIClient()

        fake_segment = type("Seg", (), {"text": " hello world "})()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([fake_segment], None)
        ai._local_whisper_model = mock_model

        result = ai.transcribe_audio("/tmp/test.mp3")
        assert result == "hello world"
        mock_model.transcribe.assert_called_once()


def test_transcribe_audio_uses_api_when_configured():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.whisper_mode = "api"
        mock_settings.openai_transcription_model = "whisper-1"

        from app.services.ai import AIClient

        ai = AIClient()
        with patch.object(ai, "_transcribe_via_api", return_value="api transcription result") as mock_api:
            result = ai.transcribe_audio("/tmp/test.mp3")
            assert result == "api transcription result"
            mock_api.assert_called_once()
