import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Answer, Document, Grade, Question, Quiz, User
from app.prompts import (
    QUIZ_GENERATOR_SYSTEM_PROMPT,
    QUIZ_GRADER_SYSTEM_PROMPT,
    build_quiz_generation_prompt,
    build_semantic_grading_prompt,
)
from app.schemas import GradeOut, QuizGenerateRequest, QuizOut, QuizSubmitRequest
from app.services.ai import ai_client


router = APIRouter(prefix="/quiz", tags=["quiz"])


def _normalize_question_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"mcq", "multiple_choice", "american", "אמריקאית"}:
        return "mcq"
    return "open"


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


def _fallback_questions(question_type: str, question_count: int) -> list[dict[str, Any]]:
    fallback: list[dict[str, Any]] = []
    for idx in range(1, question_count + 1):
        if question_type == "mcq":
            options = ["אפשרות א", "אפשרות ב", "אפשרות ג", "אפשרות ד"]
            fallback.append(
                {
                    "prompt": f"מהו הרעיון המרכזי בנושא {idx}?",
                    "type": "mcq",
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": "חפשו את ההגדרה המדויקת והקשר שלה לחומר.",
                }
            )
        else:
            fallback.append(
                {
                    "prompt": f"הסבר/י בקצרה את הנושא המרכזי מספר {idx}.",
                    "type": "open",
                    "reference_answer": "הנושא המרכזי הוא ...",
                    "explanation": "שלבו הגדרה, הסבר קצר ודוגמה.",
                }
            )
    return fallback


def _validate_generated_questions(items: list[dict[str, Any]], question_type: str, question_count: int) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in items:
        prompt = str(item.get("prompt", "")).strip()
        q_type = _normalize_question_type(str(item.get("type", question_type)))
        if not prompt:
            continue

        if q_type == "mcq":
            options = item.get("options", [])
            if not isinstance(options, list):
                continue
            clean_options = [str(option).strip() for option in options if str(option).strip()]
            deduped: list[str] = []
            for option in clean_options:
                if option not in deduped:
                    deduped.append(option)
            correct_answer = str(item.get("correct_answer", "")).strip()
            if len(deduped) != 4 or correct_answer not in deduped:
                continue
            validated.append(
                {
                    "prompt": prompt,
                    "type": "mcq",
                    "options": deduped,
                    "correct_answer": correct_answer,
                    "explanation": str(item.get("explanation", "")).strip(),
                }
            )
        else:
            reference = str(item.get("reference_answer", "")).strip()
            if not reference:
                continue
            validated.append(
                {
                    "prompt": prompt,
                    "type": "open",
                    "reference_answer": reference,
                    "explanation": str(item.get("explanation", "")).strip(),
                }
            )
        if len(validated) >= question_count:
            break
    return validated


def _heuristic_grade(expected: str, actual: str) -> tuple[float, str, str]:
    expected_tokens = {token for token in expected.lower().split() if token}
    actual_tokens = {token for token in actual.lower().split() if token}
    overlap = len(expected_tokens.intersection(actual_tokens))
    ratio = overlap / max(len(expected_tokens), 1)
    score = round(min(1.0, ratio) * 100, 2)
    if score >= 80:
        why = "התשובה מכסה רעיונות מרכזיים באופן ברור."
        improve = "כדי לשפר, הוסף/י דוגמה קצרה שתמחיש את הרעיון."
    elif score >= 45:
        why = "יש כיוון נכון, אך חסרות נקודות מהותיות."
        improve = "חזק/י את התשובה עם מונחי מפתח והסבר הקשר ביניהם."
    else:
        why = "התשובה כללית מדי ולא מכסה את לב השאלה."
        improve = "עבר/י על ההגדרה המרכזית ואז נסח/י תשובה בשלושה שלבים: הגדרה, הסבר, דוגמה."
    return score, why, improve


def _grade_with_llm(question_prompt: str, expected: str, user_answer: str) -> tuple[float, str, str, bool]:
    evaluation_prompt = build_semantic_grading_prompt(question_prompt, expected, user_answer)
    try:
        raw = ai_client.chat(QUIZ_GRADER_SYSTEM_PROMPT, evaluation_prompt)
        parsed = json.loads(raw)
        score = float(parsed.get("score_0_to_100", 0))
        score = max(0.0, min(100.0, score))
        why = str(parsed.get("why", "")).strip() or "התשובה הוערכה סמנטית ביחס לחומר."
        improve = str(parsed.get("how_to_improve", "")).strip() or "הרחב/י מעט את ההסבר והוסף/י דוגמה."
        accepted = bool(parsed.get("accepted_semantically", score >= 70))
        return score, why, improve, accepted
    except Exception:
        score, why, improve = _heuristic_grade(expected, user_answer)
        return score, why, improve, score >= 70


def _serialize_expected_answer(item: dict[str, Any]) -> str:
    if item["type"] == "mcq":
        payload = {"type": "mcq", "correct_answer": item["correct_answer"], "options": item["options"]}
    else:
        payload = {"type": "open", "reference_answer": item["reference_answer"]}
    payload["explanation"] = item.get("explanation", "")
    return json.dumps(payload, ensure_ascii=False)


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
    question_type = _normalize_question_type(payload.question_type)
    joined = "\n".join(doc.content[:1000] for doc in docs)
    prompt = build_quiz_generation_prompt(question_type, payload.question_count, payload.difficulty, joined)
    try:
        raw = ai_client.chat(QUIZ_GENERATOR_SYSTEM_PROMPT, prompt)
        parsed = json.loads(raw)
        raw_questions = parsed.get("questions", []) if isinstance(parsed, dict) else []
        if not isinstance(raw_questions, list):
            raw_questions = []
        questions = _validate_generated_questions(raw_questions, question_type, payload.question_count)
        if len(questions) < payload.question_count:
            questions.extend(_fallback_questions(question_type, payload.question_count - len(questions)))
        questions = questions[: payload.question_count]
    except json.JSONDecodeError:
        questions = _fallback_questions(question_type, payload.question_count)
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
