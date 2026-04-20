from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_chat_model
from app.agents.quiz_utils import heuristic_grade
from app.agents.state import AgentGraphState
from app.prompts import (
    PODCAST_SYSTEM_PROMPT,
    PROJECT_IDEAS_SYSTEM_PROMPT,
    QUIZ_GENERATOR_SYSTEM_PROMPT,
    QUIZ_GRADER_SYSTEM_PROMPT,
    TEACHER_SYSTEM_PROMPT,
    build_podcast_user_prompt,
    build_quiz_generation_prompt,
    build_semantic_grading_prompt,
)


def teacher_llm_reply(state: AgentGraphState) -> dict:
    user_prompt = state.get("teacher_user_prompt") or ""
    llm = get_chat_model(task="teacher", streaming=False)
    msg = llm.invoke(
        [SystemMessage(content=TEACHER_SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
    )
    text = (getattr(msg, "content", None) or "").strip()
    return {"llm_output": text, "selected_tool": "llm_chat"}


def project_ideas_llm_reply(state: AgentGraphState) -> dict:
    user_prompt = state.get("project_ideas_user_prompt") or ""
    llm = get_chat_model(task="project_ideas", streaming=False)
    msg = llm.invoke(
        [SystemMessage(content=PROJECT_IDEAS_SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
    )
    text = (getattr(msg, "content", None) or "").strip()
    return {"llm_output": text, "selected_tool": "llm_chat"}


def quiz_generation_llm(state: AgentGraphState) -> dict:
    q_type = state.get("question_type") or "open"
    count = int(state.get("question_count") or 1)
    difficulty = state.get("difficulty") or "medium"
    material = state.get("joined_doc_excerpt") or ""
    user_prompt = build_quiz_generation_prompt(q_type, count, difficulty, material)
    llm = get_chat_model(task="quiz_generate", streaming=False)
    msg = llm.invoke(
        [SystemMessage(content=QUIZ_GENERATOR_SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
    )
    raw = getattr(msg, "content", None) or ""
    return {"quiz_raw_json": str(raw).strip(), "selected_tool": "llm_json"}


def open_question_grade_llm(state: AgentGraphState) -> dict:
    q_prompt = state.get("question_prompt") or ""
    expected = state.get("reference_answer") or ""
    actual = state.get("user_answer") or ""
    evaluation_prompt = build_semantic_grading_prompt(q_prompt, expected, actual)
    llm = get_chat_model(task="quiz_grade", streaming=False)
    msg = llm.invoke(
        [SystemMessage(content=QUIZ_GRADER_SYSTEM_PROMPT), HumanMessage(content=evaluation_prompt)],
    )
    raw = getattr(msg, "content", None) or ""
    try:
        parsed = json.loads(raw)
        score = float(parsed.get("score_0_to_100", 0))
        score = max(0.0, min(100.0, score))
        why = str(parsed.get("why", "")).strip() or "התשובה הוערכה סמנטית ביחס לחומר."
        improve = str(parsed.get("how_to_improve", "")).strip() or "הרחב/י מעט את ההסבר והוסף/י דוגמה."
        accepted = bool(parsed.get("accepted_semantically", score >= 70))
        return {
            "grade_score": score,
            "grade_why": why,
            "grade_improve": improve,
            "grade_accepted": accepted,
            "selected_tool": "grade_open",
        }
    except Exception:
        score, why, improve = heuristic_grade(expected, actual)
        return {
            "grade_score": score,
            "grade_why": why,
            "grade_improve": improve,
            "grade_accepted": score >= 70,
            "errors": ["llm_grade_parse_failed"],
            "selected_tool": "grade_open",
        }


def podcast_script_llm(state: AgentGraphState) -> dict:
    content = state.get("doc_content") or ""
    user_prompt = build_podcast_user_prompt(content)
    llm = get_chat_model(task="podcast", streaming=False, temperature=0.3)
    msg = llm.invoke(
        [SystemMessage(content=PODCAST_SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
    )
    raw = getattr(msg, "content", None) or ""
    retries = int(state.get("retry_count") or 0)
    return {"script_json": str(raw).strip(), "retry_count": retries, "selected_tool": "llm_chat"}
