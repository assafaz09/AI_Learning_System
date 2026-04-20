from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


class AgentGraphState(TypedDict, total=False):
    """Shared LangGraph state across teacher, quiz, podcast, and indexing flows."""

    user_id: int
    document_ids: list[int]
    user_message: str
    learning_focus: str
    experience_label: str
    task_type: str

    retrieved_chunks: list[str]
    teacher_user_prompt: str
    project_ideas_user_prompt: str

    llm_output: str
    error_detail: str
    selected_route: str
    selected_tool: str
    errors: Annotated[list[str], operator.add]
    retry_count: int

    question_type: str
    question_count: int
    difficulty: str
    joined_doc_excerpt: str
    quiz_raw_json: str
    validated_questions: list[dict[str, Any]]

    question_prompt: str
    reference_answer: str
    user_answer: str
    grade_score: float
    grade_why: str
    grade_improve: str
    grade_accepted: bool

    doc_content: str
    script_json: str
    script_lines: list[dict[str, Any]]

    index_user_id: int
    index_document_id: int
    index_content: str
    chunks_indexed: int


TeacherRoute = Literal["build_teacher_prompt", "no_context"]
QuizGenRoute = Literal["llm_generate_quiz", "use_fallback_prompt"]
