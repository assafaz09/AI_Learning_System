from __future__ import annotations

import json

from app.agents.quiz_utils import (
    fallback_questions,
    normalize_question_type,
    validate_generated_questions,
)
from app.agents.state import AgentGraphState


def quiz_parse_and_validate(state: AgentGraphState) -> dict:
    question_type = normalize_question_type(state.get("question_type") or "open")
    question_count = int(state.get("question_count") or 1)
    raw = state.get("quiz_raw_json") or ""
    try:
        parsed = json.loads(raw)
        raw_questions = parsed.get("questions", []) if isinstance(parsed, dict) else []
        if not isinstance(raw_questions, list):
            raw_questions = []
        questions = validate_generated_questions(raw_questions, question_type, question_count)
        if len(questions) < question_count:
            questions.extend(fallback_questions(question_type, question_count - len(questions)))
        questions = questions[:question_count]
    except json.JSONDecodeError:
        questions = fallback_questions(question_type, question_count)
    return {"validated_questions": questions, "selected_tool": "llm_json"}
