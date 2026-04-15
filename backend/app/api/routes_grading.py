from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Grade, Quiz, User
from app.schemas import GradeOut


router = APIRouter(prefix="/grading", tags=["grading"])


@router.get("/{quiz_id}", response_model=GradeOut)
def get_grade(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="השאלון לא נמצא")
    grade = (
        db.query(Grade)
        .filter(Grade.quiz_id == quiz_id, Grade.user_id == user.id)
        .order_by(Grade.created_at.desc())
        .first()
    )
    if not grade:
        raise HTTPException(status_code=404, detail="לא נמצא ציון לשאלון")
    return GradeOut(score=grade.score, feedback=grade.feedback)
