import os
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test.db'}"
os.environ["QDRANT_URL"] = "http://invalid-qdrant:6333"
os.environ["OPENAI_API_KEY"] = ""

from app.main import app  # noqa: E402


client = TestClient(app)


def _mock_embed(_: str) -> list[float]:
    return [0.1] * 64


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

    with patch("app.api.routes_documents.ai_client.embed", side_effect=_mock_embed):
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
    ):
        uploaded = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("study.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )
    assert uploaded.status_code == 200
    assert uploaded.json()["name"] == "study.pdf"
