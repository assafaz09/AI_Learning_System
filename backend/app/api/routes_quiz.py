from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Answer, Document, Grade, Question, Quiz, User
from app.schemas import GradeOut, QuizGenerateRequest, QuizOut, QuizSubmitRequest
from app.services.ai import ai_client


router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="השאלון לא נמצא")
    return quiz


@router.post("/generate", response_model=QuizOut)
def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(payload.document_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים")
    joined = "\n".join(doc.content[:1000] for doc in docs)
    prompt = (
        f"צור {payload.question_count} שאלות פתוחות קצרות מהחומר הבא "
        f"ברמת קושי {payload.difficulty}. החזר בפורמט שורות עם 'Q:' ו-'A:'.\n\n{joined}"
    )
    try:
        raw = ai_client.chat("אתה סוכן שמחולל שאלוני לימוד איכותיים.", prompt)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    qa_pairs: list[tuple[str, str]] = []
    current_q = None
    for line in lines:
        if line.startswith("Q:"):
            current_q = line.removeprefix("Q:").strip()
        elif line.startswith("A:") and current_q:
            qa_pairs.append((current_q, line.removeprefix("A:").strip()))
            current_q = None

    if not qa_pairs:
        qa_pairs = [(f"מהו הרעיון המרכזי מספר {idx}?", "הרעיון המרכזי הוא ...") for idx in range(1, payload.question_count + 1)]

    quiz = Quiz(user_id=user.id, title="שאלון שנוצר על ידי AI")
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    for question, expected in qa_pairs[: payload.question_count]:
        db.add(Question(quiz_id=quiz.id, prompt=question, expected_answer=expected))
    db.commit()
    db.refresh(quiz)
    return quiz


@router.post("/{quiz_id}/submit", response_model=GradeOut)
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="השאלון לא נמצא")
    questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="לשאלון אין שאלות")

    score_acc = 0.0
    feedback_items = []
    for question in questions:
        user_answer = payload.answers.get(question.id, "")
        db.add(Answer(question_id=question.id, user_id=user.id, answer_text=user_answer))
        expected_tokens = set(question.expected_answer.lower().split())
        answer_tokens = set(user_answer.lower().split())
        overlap = len(expected_tokens.intersection(answer_tokens))
        max_tokens = max(len(expected_tokens), 1)
        q_score = min(1.0, overlap / max_tokens)
        score_acc += q_score
        feedback_items.append(f"שאלה {question.id}: התאמה של {round(q_score * 100)}%")
    db.commit()

    final_score = round((score_acc / len(questions)) * 100, 2)
    feedback = "; ".join(feedback_items)
    db.add(Grade(quiz_id=quiz.id, user_id=user.id, score=final_score, feedback=feedback))
    db.commit()
    return GradeOut(score=final_score, feedback=feedback)
