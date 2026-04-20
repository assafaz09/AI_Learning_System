"""Shared quiz generation validation (used by API routes and LangGraph)."""

from __future__ import annotations

from typing import Any


def normalize_question_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"mcq", "multiple_choice", "american", "אמריקאית"}:
        return "mcq"
    return "open"


def fallback_questions(question_type: str, question_count: int) -> list[dict[str, Any]]:
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


def validate_generated_questions(
    items: list[dict[str, Any]], question_type: str, question_count: int
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in items:
        prompt = str(item.get("prompt", "")).strip()
        q_type = normalize_question_type(str(item.get("type", question_type)))
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


def heuristic_grade(expected: str, actual: str) -> tuple[float, str, str]:
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
