from __future__ import annotations

from app.agents.state import AgentGraphState
from app.prompts import build_project_ideas_user_prompt, build_teacher_user_prompt
from app.services.ai import ai_client
from app.services.vector_store import VectorStore


def teacher_retrieve_and_prompt(state: AgentGraphState, vector_store: VectorStore) -> dict:
    message = state.get("user_message") or ""
    user_id = state["user_id"]
    doc_ids = state.get("document_ids") or []
    user_vector = ai_client.embed(message)
    contexts = vector_store.search(user_vector, user_id=user_id, document_ids=doc_ids, limit=5)
    if not contexts:
        return {
            "retrieved_chunks": [],
            "error_detail": "לא נמצאו מקטעים סמנטיים למסמכים שנבחרו. יש לבצע אינדוקס מחדש או לבדוק חיבור ל-Qdrant",
            "selected_tool": "retrieval",
        }
    prompt = build_teacher_user_prompt(message, contexts)
    return {
        "retrieved_chunks": contexts,
        "teacher_user_prompt": prompt,
        "selected_tool": "retrieval",
        "error_detail": "",
    }


def project_ideas_retrieve_and_prompt(state: AgentGraphState, vector_store: VectorStore) -> dict:
    learning_focus = state.get("learning_focus") or ""
    experience_label = state.get("experience_label") or ""
    user_id = state["user_id"]
    doc_ids = state.get("document_ids") or []
    embed_text = f"{learning_focus}\n{experience_label}"
    user_vector = ai_client.embed(embed_text)
    contexts = vector_store.search(user_vector, user_id=user_id, document_ids=doc_ids, limit=8)
    if not contexts:
        return {
            "retrieved_chunks": [],
            "error_detail": "לא נמצאו מקטעים סמנטיים למסמכים שנבחרו. יש לבצע אינדוקס מחדש או לבדוק חיבור ל-Qdrant",
            "selected_tool": "retrieval",
        }
    prompt = build_project_ideas_user_prompt(contexts, learning_focus, experience_label)
    return {
        "retrieved_chunks": contexts,
        "project_ideas_user_prompt": prompt,
        "selected_tool": "retrieval",
        "error_detail": "",
    }
