from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.tracing import graph_run_metadata
from app.api.dependencies import get_current_user
from app.api.routes_documents import vector_store
from app.db import get_db
from app.models import Document, GroupLearningMessage, GroupLearningSession, User
from app.schemas import (
    GroupLearningMessageOut,
    GroupLearningMessagesResponse,
    GroupLearningPostMessage,
    GroupLearningReplyOut,
    GroupLearningSessionCreate,
    GroupLearningSessionOut,
)
from app.services.group_peer_chat import run_group_peer_turn

router = APIRouter(prefix="/group-learning", tags=["group-learning"])


def _resolve_session_document_ids(document_ids: list[int], db: Session, user: User) -> list[int]:
    unique = sorted(set(document_ids))
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(unique)).all()
    if len(docs) != len(unique):
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים תקינים")
    return unique


@router.post("/sessions", response_model=GroupLearningSessionOut)
def create_group_session(
    payload: GroupLearningSessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    selected = _resolve_session_document_ids(payload.document_ids, db, user)
    title = payload.title or "למידה בקבוצה"
    row = GroupLearningSession(
        user_id=user.id,
        title=title,
        document_ids_json=json.dumps(selected),
        next_speaker="novice",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return GroupLearningSessionOut(
        id=row.id,
        title=row.title,
        document_ids=json.loads(row.document_ids_json),
        next_speaker=row.next_speaker,
    )


@router.post("/sessions/{session_id}/message", response_model=GroupLearningReplyOut)
def post_group_message(
    session_id: int,
    payload: GroupLearningPostMessage,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(GroupLearningSession)
        .filter(GroupLearningSession.id == session_id, GroupLearningSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="הסשן לא נמצא")

    speaker = session.next_speaker
    workflow = f"group_peer_{speaker}"
    cfg = RunnableConfig(tags=["group_learning", workflow], metadata=graph_run_metadata(workflow))
    try:
        reply, used_speaker = run_group_peer_turn(
            db, vector_store, session, payload.message, config=cfg
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    return GroupLearningReplyOut(session_id=session_id, reply=reply, speaker=used_speaker)


@router.get("/sessions/{session_id}/messages", response_model=GroupLearningMessagesResponse)
def list_group_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(GroupLearningSession)
        .filter(GroupLearningSession.id == session_id, GroupLearningSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="הסשן לא נמצא")

    rows = (
        db.query(GroupLearningMessage)
        .filter(GroupLearningMessage.session_id == session_id)
        .order_by(GroupLearningMessage.created_at.asc(), GroupLearningMessage.id.asc())
        .all()
    )
    return GroupLearningMessagesResponse(
        session_id=session_id,
        messages=[
            GroupLearningMessageOut(
                id=r.id, role=r.role, content=r.content, created_at=r.created_at.isoformat()
            )
            for r in rows
        ],
    )


@router.get("/sessions", response_model=list[GroupLearningSessionOut])
def list_group_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(GroupLearningSession)
        .filter(GroupLearningSession.user_id == user.id)
        .order_by(GroupLearningSession.updated_at.desc(), GroupLearningSession.id.desc())
        .all()
    )
    return [
        GroupLearningSessionOut(
            id=r.id,
            title=r.title,
            document_ids=json.loads(r.document_ids_json),
            next_speaker=r.next_speaker,
        )
        for r in rows
    ]
