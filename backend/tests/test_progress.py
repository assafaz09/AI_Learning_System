import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test_progress.db'}"
os.environ["QDRANT_URL"] = "http://invalid-qdrant:6333"
os.environ["OPENAI_API_KEY"] = ""

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Conversation, Document, Grade, LearningProject, Message, Quiz  # noqa: E402


Base.metadata.create_all(bind=engine)
client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    payload = {"email": f"progress-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    assert register.status_code == 200
    return {"Authorization": f"Bearer {register.json()['access_token']}"}


def test_progress_dashboard_empty_user():
    headers = _auth_headers()
    response = client.get("/progress", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["documents_count"] == 0
    assert body["summary"]["overall_progress_percent"] == 0
    assert body["quiz_scores_timeline"] == []
    assert len(body["activity_last_14_days"]) == 14
    assert body["insights"]


def test_progress_dashboard_with_activity():
    payload = {"email": f"progress-{uuid4()}@example.com", "password": "Secret123"}
    register = client.post("/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == payload["email"]).one()
        user_id = user.id

        doc = Document(
            user_id=user_id,
            name="notes.txt",
            content="Python basics",
            path="/tmp/notes.txt",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        conv = Conversation(user_id=user_id, title="שאלות")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        db.add(Message(conversation_id=conv.id, role="user", content="מה זה Python?"))
        db.add(Message(conversation_id=conv.id, role="assistant", content="שפת תכנות"))

        quiz = Quiz(user_id=user_id, title="בוחן 1")
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        db.add(Grade(quiz_id=quiz.id, user_id=user_id, score=82.0, feedback="טוב"))

        db.add(
            LearningProject(
                user_id=user_id,
                title="פרויקט",
                suggestions_body="",
                learning_focus="Python",
                experience_band="beginner_short",
                document_ids_json="[]",
                status="in_progress",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/progress", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["documents_count"] == 1
    assert body["summary"]["teacher_messages_count"] == 1
    assert body["summary"]["quizzes_graded"] == 1
    assert body["summary"]["average_quiz_score"] == 82.0
    assert body["summary"]["projects_in_progress"] == 1
    assert body["summary"]["overall_progress_percent"] > 0
    assert len(body["quiz_scores_timeline"]) == 1
    assert body["activity_breakdown"]["teacher_messages"] == 1
