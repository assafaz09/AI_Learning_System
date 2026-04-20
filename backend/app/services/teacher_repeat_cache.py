"""Reuse prior teacher replies when the same question is asked again (same chat + document scope)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Message


def normalize_teacher_message(text: str) -> str:
    return " ".join(text.split()).strip()


def document_scope_json(document_ids: list[int]) -> str:
    return json.dumps(sorted(document_ids))


def find_prior_teacher_answer(
    db: Session,
    conversation_id: int,
    normalized_message: str,
    scope_json: str,
) -> str | None:
    """Return the last assistant answer for this normalized question and document scope in the thread."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    last_answer: str | None = None
    for i in range(len(messages) - 1):
        user_m, asst_m = messages[i], messages[i + 1]
        if user_m.role != "user" or asst_m.role != "assistant":
            continue
        if (user_m.document_scope_json or "") != scope_json:
            continue
        if normalize_teacher_message(user_m.content) != normalized_message:
            continue
        last_answer = asst_m.content
    return last_answer
