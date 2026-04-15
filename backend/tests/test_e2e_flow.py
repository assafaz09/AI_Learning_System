import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test_e2e.db'}"
os.environ["QDRANT_URL"] = "http://invalid-qdrant:6333"
os.environ["OPENAI_API_KEY"] = ""

from app.main import app  # noqa: E402


def _mock_embed(_: str) -> list[float]:
    return [0.1] * 64


def _mock_chat(_: str, __: str) -> str:
    return "Q: מהי ירידת מפל\nA: שיטת אופטימיזציה איטרטיבית"


def test_end_to_end_learning_flow():
    client = TestClient(app)

    reg = client.post("/auth/register", json={"email": "flow@example.com", "password": "FlowPass123"})
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_teacher.ai_client.embed", side_effect=_mock_embed
    ), patch("app.api.routes_teacher.ai_client.chat", side_effect=_mock_chat), patch(
        "app.api.routes_quiz.ai_client.chat", side_effect=_mock_chat
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study.txt", b"Neural networks have layers and learn by gradient descent.", "text/plain")},
        )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]
    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed):
        uploaded_two = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study2.txt", b"Backpropagation updates weights using gradients.", "text/plain")},
        )
    assert uploaded_two.status_code == 200
    doc_two_id = uploaded_two.json()["id"]

    selected = client.put("/documents/selected", headers=headers, json={"document_ids": [doc_id, doc_two_id]})
    assert selected.status_code == 200

    with patch("app.api.routes_teacher.ai_client.embed", side_effect=_mock_embed), patch(
        "app.api.routes_teacher.ai_client.chat", side_effect=_mock_chat
    ):
        teacher = client.post(
            "/teacher/chat",
            headers=headers,
            json={"message": "What is gradient descent?"},
        )
    assert teacher.status_code == 200

    with patch("app.api.routes_quiz.ai_client.chat", side_effect=_mock_chat):
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
    grade = client.post(f"/quiz/{quiz_id}/submit", headers=headers, json={"answers": answers})
    assert grade.status_code == 200
    assert "score" in grade.json()
