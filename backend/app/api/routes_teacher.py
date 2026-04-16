import json
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes_documents import vector_store
from app.db import get_db
from app.models import Conversation, Document, Message, User, UserDocumentSelection
from app.prompts import TEACHER_SYSTEM_PROMPT, build_teacher_user_prompt
from app.schemas import TeacherChatRequest, TeacherChatResponse, TeacherConversationMessagesResponse, TeacherMessageOut
from app.services.ai import ai_client


router = APIRouter(prefix="/teacher", tags=["teacher"])


def _resolve_selected_documents(payload: TeacherChatRequest, db: Session, user: User) -> list[int]:
    selected_ids = payload.document_ids or [
        row[0]
        for row in db.query(UserDocumentSelection.document_id).filter(UserDocumentSelection.user_id == user.id).all()
    ]
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(selected_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים תקינים")
    return selected_ids


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


def _build_prompt(message: str, selected_ids: list[int], user_id: int) -> str:
    user_vector = ai_client.embed(message)
    contexts = vector_store.search(user_vector, user_id=user_id, document_ids=selected_ids, limit=5)
    if not contexts:
        raise HTTPException(
            status_code=409,
            detail="לא נמצאו מקטעים סמנטיים למסמכים שנבחרו. יש לבצע אינדוקס מחדש או לבדוק חיבור ל-Qdrant",
        )
    return build_teacher_user_prompt(message, contexts)


@router.post("/chat", response_model=TeacherChatResponse)
def teacher_chat(payload: TeacherChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected_ids = _resolve_selected_documents(payload, db, user)
    conversation = _resolve_conversation(payload, db, user)

    try:
        prompt = _build_prompt(payload.message, selected_ids, user.id)
        answer = ai_client.chat(TEACHER_SYSTEM_PROMPT, prompt)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    return TeacherChatResponse(conversation_id=conversation.id, answer=answer)


@router.post("/chat/stream")
def teacher_chat_stream(payload: TeacherChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected_ids = _resolve_selected_documents(payload, db, user)
    conversation = _resolve_conversation(payload, db, user)

    try:
        prompt = _build_prompt(payload.message, selected_ids, user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    def stream_events() -> Generator[str, None, None]:
        answer_parts: list[str] = []
        try:
            for delta in ai_client.chat_stream(TEACHER_SYSTEM_PROMPT, prompt):
                answer_parts.append(delta)
                yield f"event: delta\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'detail': f'שגיאת חיבור ל-LLM: {exc}'}, ensure_ascii=False)}\n\n"
            return

        answer = "".join(answer_parts).strip()
        if not answer:
            answer = "לא התקבלה תשובה מהמודל."
        db.add(Message(conversation_id=conversation.id, role="user", content=payload.message))
        db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
        db.commit()
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation.id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")


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
