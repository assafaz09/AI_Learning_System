from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Conversation, Grade, Quiz, User


router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def get_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversations = db.query(Conversation).filter(Conversation.user_id == user.id).order_by(Conversation.created_at.desc()).all()
    quizzes = db.query(Quiz).filter(Quiz.user_id == user.id).order_by(Quiz.created_at.desc()).all()
    grades = db.query(Grade).filter(Grade.user_id == user.id).order_by(Grade.created_at.desc()).all()
    return {
        "conversations": [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in conversations],
        "quizzes": [{"id": q.id, "title": q.title, "created_at": q.created_at} for q in quizzes],
        "grades": [{"id": g.id, "quiz_id": g.quiz_id, "score": g.score, "created_at": g.created_at} for g in grades],
    }
