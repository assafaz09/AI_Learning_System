import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test_e2e.db'}"
os.environ["QDRANT_URL"] = "http://invalid-qdrant:6333"
os.environ["OPENAI_API_KEY"] = ""

from app.main import app  # noqa: E402


def _mock_embed(_: str) -> list[float]:
    return [0.1] * 64


def _e2e_chat_model() -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Q: מהי ירידת מפל\nA: שיטת אופטימיזציה איטרטיבית"
    )
    return mock_llm


def _mock_chunk_id() -> str:
    from uuid import uuid4

    return str(uuid4())


def test_end_to_end_learning_flow():
    client = TestClient(app)

    reg = client.post("/auth/register", json={"email": "flow@example.com", "password": "FlowPass123"})
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch(
        "app.api.routes_documents.vector_store.upsert_chunk", return_value=None
    ), patch(
        "app.api.routes_teacher.vector_store.search", return_value=["Gradient descent optimizes iteratively."]
    ), patch("app.services.ai.ai_client.embed", side_effect=_mock_embed), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=_e2e_chat_model()
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study.txt", b"Neural networks have layers and learn by gradient descent.", "text/plain")},
        )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]
    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_documents.vector_store.new_chunk_id", side_effect=_mock_chunk_id
    ), patch("app.api.routes_documents.vector_store.upsert_chunk", return_value=None):
        uploaded_two = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study2.txt", b"Backpropagation updates weights using gradients.", "text/plain")},
        )
    assert uploaded_two.status_code == 200
    doc_two_id = uploaded_two.json()["id"]

    selected = client.put("/documents/selected", headers=headers, json={"document_ids": [doc_id, doc_two_id]})
    assert selected.status_code == 200

    with patch("app.services.ai.ai_client.embed", side_effect=_mock_embed), patch(
        "app.agents.nodes.llm_nodes.get_chat_model", return_value=_e2e_chat_model()
    ):
        teacher = client.post(
            "/teacher/chat",
            headers=headers,
            json={"message": "What is gradient descent?"},
        )
    assert teacher.status_code == 200

    with patch("app.agents.nodes.llm_nodes.get_chat_model", return_value=_e2e_chat_model()):
        quiz = client.post(
            "/quiz/generate",
            headers=headers,
            json={"document_ids": [doc_id], "difficulty": "medium", "question_count": 3},
        )
    assert quiz.status_code == 200
    quiz_id = quiz.json()["id"]
    questions = quiz.json()["questions"]
    assert len(questions) > 0

    answers = {question["id"]: "Gradient descent optimizes model parameters iteratively." for question in questions}
    with patch("app.agents.nodes.llm_nodes.get_chat_model", return_value=_e2e_chat_model()):
        grade = client.post(f"/quiz/{quiz_id}/submit", headers=headers, json={"answers": answers})
    assert grade.status_code == 200
    assert "score" in grade.json()
