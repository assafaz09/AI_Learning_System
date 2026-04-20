import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.graphs.quiz import invoke_open_grade, invoke_quiz_generate
from app.agents.quiz_utils import normalize_question_type
from app.agents.tracing import graph_run_metadata
from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Answer, Document, Grade, Question, Quiz, User
from app.schemas import GradeOut, QuizGenerateRequest, QuizOut, QuizSubmitRequest

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _extract_question_payload(question: Question) -> dict[str, Any]:
    try:
        payload = json.loads(question.expected_answer)
        if isinstance(payload, dict) and "type" in payload:
            return payload
    except Exception:
        pass
    return {"type": "open", "reference_answer": question.expected_answer, "explanation": ""}


def _to_question_out(question: Question) -> dict[str, Any]:
    payload = _extract_question_payload(question)
    return {
        "id": question.id,
        "prompt": question.prompt,
        "question_type": payload.get("type", "open"),
        "options": payload.get("options", []),
    }


def _serialize_expected_answer(item: dict[str, Any]) -> str:
    if item["type"] == "mcq":
        payload = {"type": "mcq", "correct_answer": item["correct_answer"], "options": item["options"]}
    else:
        payload = {"type": "open", "reference_answer": item["reference_answer"]}
    payload["explanation"] = item.get("explanation", "")
    return json.dumps(payload, ensure_ascii=False)


def _grade_with_llm(question_prompt: str, expected: str, user_answer: str) -> tuple[float, str, str, bool]:
    cfg = RunnableConfig(tags=["quiz", "grade_open"], metadata=graph_run_metadata("quiz_grade_open"))
    out = invoke_open_grade(
        {
            "question_prompt": question_prompt,
            "reference_answer": expected,
            "user_answer": user_answer,
        },
        config=cfg,
    )
    score = float(out.get("grade_score") or 0.0)
    why = str(out.get("grade_why") or "")
    improve = str(out.get("grade_improve") or "")
    accepted = bool(out.get("grade_accepted"))
    return score, why, improve, accepted


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="השאלון לא נמצא")
    return {"id": quiz.id, "title": quiz.title, "questions": [_to_question_out(question) for question in quiz.questions]}


@router.post("/generate", response_model=QuizOut)
def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == user.id, Document.id.in_(payload.document_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים")
    question_type = normalize_question_type(payload.question_type)
    joined = "\n".join(doc.content[:1000] for doc in docs)
    try:
        cfg = RunnableConfig(tags=["quiz", "generate"], metadata=graph_run_metadata("quiz_generate"))
        out = invoke_quiz_generate(
            {
                "question_type": question_type,
                "question_count": payload.question_count,
                "difficulty": payload.difficulty,
                "joined_doc_excerpt": joined,
            },
            config=cfg,
        )
        questions = out.get("validated_questions") or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM: {exc}") from exc

    quiz = Quiz(user_id=user.id, title="שאלון שנוצר על ידי AI")
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    for item in questions:
        expected = _serialize_expected_answer(item)
        db.add(Question(quiz_id=quiz.id, prompt=item["prompt"], expected_answer=expected))
    db.commit()
    db.refresh(quiz)
    return {"id": quiz.id, "title": quiz.title, "questions": [_to_question_out(question) for question in quiz.questions]}


@router.post("/{quiz_id}/submit", response_model=GradeOut)
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="השאלון לא נמצא")
    questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="לשאלון אין שאלות")

    score_acc = 0.0
    feedback_items: list[dict[str, Any]] = []
    for question in questions:
        user_answer = payload.answers.get(question.id, "")
        db.add(Answer(question_id=question.id, user_id=user.id, answer_text=user_answer))
        expected_payload = _extract_question_payload(question)
        q_type = expected_payload.get("type", "open")
        if q_type == "mcq":
            expected = str(expected_payload.get("correct_answer", ""))
            raw_score = 100.0 if user_answer.strip() == expected else 0.0
            why = "בחרת בתשובה הנכונה." if raw_score == 100 else f"התשובה הנכונה היא: {expected}."
            improve = str(expected_payload.get("explanation", "")).strip() or "חפש/י בשאלה רמזים שמובילים לאפשרות המדויקת."
            accepted = raw_score >= 70
        else:
            expected = str(expected_payload.get("reference_answer", ""))
            raw_score, why, improve, accepted = _grade_with_llm(question.prompt, expected, user_answer)
        score_acc += raw_score

        feedback_items.append(
            {
                "question_id": question.id,
                "prompt": question.prompt,
                "your_answer": user_answer or "לא ניתנה תשובה",
                "expected_core": expected,
                "why": why,
                "how_to_improve": improve,
                "accepted_semantically": accepted,
                "score": round(raw_score, 2),
            }
        )
    db.commit()

    final_score = round(score_acc / len(questions), 2)
    strengths = [item for item in feedback_items if item["score"] >= 75]
    weaknesses = [item for item in feedback_items if item["score"] < 75]
    summary = (
        f"ציון כולל: {final_score}. "
        f"ענית טוב על {len(strengths)} שאלות, וב-{len(weaknesses)} שאלות יש מקום לשיפור."
    )
    feedback_payload = {"summary": summary, "items": feedback_items}
    db.add(Grade(quiz_id=quiz.id, user_id=user.id, score=final_score, feedback=json.dumps(feedback_payload, ensure_ascii=False)))
    db.commit()
    return GradeOut(score=final_score, feedback=summary, feedback_items=feedback_items)
