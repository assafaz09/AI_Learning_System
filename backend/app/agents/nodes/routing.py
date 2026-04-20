from __future__ import annotations

from typing import Literal

from app.agents.state import AgentGraphState, QuizGenRoute, TeacherRoute


def route_after_teacher_retrieval(state: AgentGraphState) -> TeacherRoute:
    if state.get("error_detail"):
        return "no_context"
    chunks = state.get("retrieved_chunks") or []
    if not chunks:
        return "no_context"
    return "build_teacher_prompt"


def route_quiz_generation(state: AgentGraphState) -> QuizGenRoute:
    excerpt = (state.get("joined_doc_excerpt") or "").strip()
    if len(excerpt) < 20:
        return "use_fallback_prompt"
    return "llm_generate_quiz"


def route_podcast_parse(state: AgentGraphState) -> Literal["tts_ready", "retry_script", "script_failed"]:
    if state.get("script_lines"):
        return "tts_ready"
    retries = int(state.get("retry_count") or 0)
    if retries < 2:
        return "retry_script"
    return "script_failed"
