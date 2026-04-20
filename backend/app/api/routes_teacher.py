import json
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes_documents import vector_store
from app.db import get_db
from app.models import Conversation, Document, LearningProject, Message, User, UserDocumentSelection
from langchain_core.runnables import RunnableConfig

from app.agents.graphs.teacher import (
    invoke_project_ideas,
    invoke_teacher_chat,
    iter_teacher_reply_stream,
    teacher_retrieval_phase,
)
from app.agents.tracing import graph_run_metadata
from app.services.teacher_repeat_cache import (
    document_scope_json,
    find_prior_teacher_answer,
    normalize_teacher_message,
)
from app.schemas import (
    ProjectIdeasRequest,
    ProjectIdeasResponse,
    SavedProjectCreate,
    SavedProjectCreateAI,
    SavedProjectCreateManual,
    SavedProjectOut,
    SavedProjectUpdate,
    TeacherChatRequest,
    TeacherChatResponse,
    TeacherConversationMessagesResponse,
    TeacherMessageOut,
)
router = APIRouter(prefix="/teacher", tags=["teacher"])

_EXPERIENCE_BAND_LABELS: dict[str, str] = {
    "beginner_short": "מתחיל · עד כמה שעות (פרויקט קצר)",
    "intermediate_days": "ביניים · מספר ימים",
    "advanced_extended": "מעמיק · פרויקט מורחב",
}


def _resolve_document_ids(document_ids: list[int] | None, db: Session, user: User) -> list[int]:
    selected_ids = document_ids or [
        row[0]
        for row in db.query(UserDocumentSelection.document_id).filter(UserDocumentSelection.user_id == user.id).all()
    ]
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(selected_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים תקינים")
    return selected_ids


def _resolve_selected_documents(payload: TeacherChatRequest, db: Session, user: User) -> list[int]:
    return _resolve_document_ids(payload.document_ids, db, user)


def _resolve_conversation(payload: TeacherChatRequest, db: Session, user: User) -> Conversation:
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="השיחה לא נמצאה")
        return conversation

    conversation = Conversation(user_id=user.id, title=(payload.message[:64] or "שיחה עם מורה"))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/chat", response_model=TeacherChatResponse)
def teacher_chat(payload: TeacherChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected_ids = _resolve_selected_documents(payload, db, user)
    conversation = _resolve_conversation(payload, db, user)
    scope_json = document_scope_json(selected_ids)
    norm_q = normalize_teacher_message(payload.message)
    cached = find_prior_teacher_answer(db, conversation.id, norm_q, scope_json)
    if cached is not None:
        db.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=payload.message,
                document_scope_json=scope_json,
            )
        )
        db.add(Message(conversation_id=conversation.id, role="assistant", content=cached))
        db.commit()
        return TeacherChatResponse(conversation_id=conversation.id, answer=cached, from_cache=True)

    try:
        cfg = RunnableConfig(tags=["teacher", "chat"], metadata=graph_run_metadata("teacher_chat"))
        out = invoke_teacher_chat(
            vector_store,
            {"user_id": user.id, "document_ids": selected_ids, "user_message": payload.message},
            config=cfg,
        )
        if out.get("error_detail"):
            raise HTTPException(status_code=409, detail=out["error_detail"])
        answer = (out.get("llm_output") or "").strip() or "לא התקבלה תשובה מהמודל."
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.message,
            document_scope_json=scope_json,
        )
    )
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    return TeacherChatResponse(conversation_id=conversation.id, answer=answer, from_cache=False)


@router.post("/chat/stream")
def teacher_chat_stream(payload: TeacherChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected_ids = _resolve_selected_documents(payload, db, user)
    conversation = _resolve_conversation(payload, db, user)
    scope_json = document_scope_json(selected_ids)
    norm_q = normalize_teacher_message(payload.message)
    cached = find_prior_teacher_answer(db, conversation.id, norm_q, scope_json)

    def stream_cached() -> Generator[str, None, None]:
        yield f"event: delta\ndata: {json.dumps({'delta': cached}, ensure_ascii=False)}\n\n"
        db.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=payload.message,
                document_scope_json=scope_json,
            )
        )
        db.add(Message(conversation_id=conversation.id, role="assistant", content=cached))
        db.commit()
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation.id, 'from_cache': True}, ensure_ascii=False)}\n\n"

    if cached is not None:
        return StreamingResponse(stream_cached(), media_type="text/event-stream")

    try:
        merged = teacher_retrieval_phase(
            vector_store, user_id=user.id, document_ids=selected_ids, message=payload.message
        )
        if merged.get("error_detail"):
            raise HTTPException(status_code=409, detail=merged["error_detail"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    def stream_live() -> Generator[str, None, None]:
        answer_parts: list[str] = []
        try:
            for delta in iter_teacher_reply_stream(merged):
                answer_parts.append(delta)
                yield f"event: delta\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'detail': f'שגיאת חיבור ל-LLM: {exc}'}, ensure_ascii=False)}\n\n"
            return

        answer = "".join(answer_parts).strip()
        if not answer:
            answer = "לא התקבלה תשובה מהמודל."
        db.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=payload.message,
                document_scope_json=scope_json,
            )
        )
        db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
        db.commit()
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation.id, 'from_cache': False}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream_live(), media_type="text/event-stream")


@router.post("/project-ideas", response_model=ProjectIdeasResponse)
def teacher_project_ideas(
    payload: ProjectIdeasRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    selected_ids = _resolve_document_ids(payload.document_ids, db, user)
    experience_label = _EXPERIENCE_BAND_LABELS[payload.experience_band]

    try:
        cfg = RunnableConfig(tags=["teacher", "project_ideas"], metadata=graph_run_metadata("teacher_project_ideas"))
        out = invoke_project_ideas(
            vector_store,
            {
                "user_id": user.id,
                "document_ids": selected_ids,
                "learning_focus": payload.learning_focus,
                "experience_label": experience_label,
            },
            config=cfg,
        )
        if out.get("error_detail"):
            raise HTTPException(status_code=409, detail=out["error_detail"])
        suggestions = out.get("llm_output") or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    text = (suggestions or "").strip()
    if not text:
        text = "לא התקבלה תשובה מהמודל."
    return ProjectIdeasResponse(suggestions=text)


def _learning_project_to_out(row: LearningProject) -> SavedProjectOut:
    doc_ids = json.loads(row.document_ids_json)
    kind = row.source if row.source in ("ai", "manual") else "ai"
    return SavedProjectOut(
        id=row.id,
        kind=kind,
        title=row.title,
        suggestions_body=row.suggestions_body,
        learning_focus=row.learning_focus,
        experience_band=row.experience_band,
        document_ids=doc_ids,
        importance=row.importance,
        description=row.description,
        status=row.status,
        notes=row.notes,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


@router.get("/saved-projects", response_model=list[SavedProjectOut])
def list_saved_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(LearningProject)
        .filter(LearningProject.user_id == user.id)
        .order_by(LearningProject.created_at.desc(), LearningProject.id.desc())
        .all()
    )
    return [_learning_project_to_out(r) for r in rows]


@router.post("/saved-projects", response_model=SavedProjectOut)
def create_saved_project(
    payload: SavedProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if isinstance(payload, SavedProjectCreateAI):
        row = LearningProject(
            user_id=user.id,
            title=payload.title,
            suggestions_body=payload.suggestions_body,
            learning_focus=payload.learning_focus,
            experience_band=payload.experience_band,
            document_ids_json=json.dumps(payload.document_ids),
            source="ai",
            importance="medium",
            description=None,
            status="not_started",
            notes=None,
        )
    else:
        row = LearningProject(
            user_id=user.id,
            title=payload.title,
            suggestions_body="",
            learning_focus="",
            experience_band="manual",
            document_ids_json=json.dumps([]),
            source="manual",
            importance=payload.importance,
            description=payload.description,
            status=payload.status,
            notes=None,
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _learning_project_to_out(row)


@router.patch("/saved-projects/{project_id}", response_model=SavedProjectOut)
def update_saved_project(
    project_id: int,
    payload: SavedProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(LearningProject)
        .filter(LearningProject.id == project_id, LearningProject.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="אין שדות לעדכון")

    if "title" in data:
        row.title = data["title"]
    if "status" in data:
        row.status = data["status"]
    if "notes" in data:
        row.notes = data["notes"]
    if "importance" in data:
        row.importance = data["importance"]
    if "description" in data:
        row.description = data["description"]

    db.commit()
    db.refresh(row)
    return _learning_project_to_out(row)


@router.delete("/saved-projects/{project_id}", status_code=204)
def delete_saved_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = (
        db.query(LearningProject)
        .filter(LearningProject.id == project_id, LearningProject.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
    db.delete(row)
    db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=TeacherConversationMessagesResponse)
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="השיחה לא נמצאה")

    messages = (
        db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc(), Message.id.asc()).all()
    )
    return TeacherConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            TeacherMessageOut(id=item.id, role=item.role, content=item.content, created_at=item.created_at.isoformat())
            for item in messages
        ],
    )
