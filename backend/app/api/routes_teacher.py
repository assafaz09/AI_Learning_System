from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes_documents import vector_store
from app.db import get_db
from app.models import Conversation, Document, Message, User, UserDocumentSelection
from app.schemas import TeacherChatRequest, TeacherChatResponse
from app.services.ai import ai_client


router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.post("/chat", response_model=TeacherChatResponse)
def teacher_chat(payload: TeacherChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected_ids = payload.document_ids or [
        row[0]
        for row in db.query(UserDocumentSelection.document_id).filter(UserDocumentSelection.user_id == user.id).all()
    ]
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(selected_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים תקינים")

    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="השיחה לא נמצאה")
    else:
        conversation = Conversation(user_id=user.id, title=(payload.message[:64] or "שיחה עם מורה"))
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    try:
        user_vector = ai_client.embed(payload.message)
        contexts = vector_store.search(user_vector, user_id=user.id, document_ids=selected_ids, limit=5)
        if not contexts:
            raise HTTPException(
                status_code=409,
                detail="לא נמצאו מקטעים סמנטיים למסמכים שנבחרו. יש לבצע אינדוקס מחדש או לבדוק חיבור ל-Qdrant",
            )
        prompt = (
            "אתה סוכן מורה חכם. ענה רק על בסיס ההקשר שסופק לך.\n\n"
            f"הקשר:\n{chr(10).join(contexts)}\n\n"
            f"שאלה: {payload.message}"
        )
        answer = ai_client.chat("אתה סוכן מורה בפלטפורמת למידה מבוססת AI.", prompt)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    return TeacherChatResponse(conversation_id=conversation.id, answer=answer)
