from app.prompts import (
    QUIZ_GENERATOR_SYSTEM_PROMPT,
    QUIZ_GRADER_SYSTEM_PROMPT,
    TEACHER_SYSTEM_PROMPT,
    build_quiz_generation_prompt,
    build_semantic_grading_prompt,
    build_teacher_user_prompt,
)


def test_teacher_prompt_builder_includes_context_and_question():
    prompt = build_teacher_user_prompt("מה זה גרדיאנט?", ["הקשר ראשון", "הקשר שני"])
    assert "מה זה גרדיאנט?" in prompt
    assert "הקשר ראשון" in prompt
    assert "הקשר שני" in prompt
    assert TEACHER_SYSTEM_PROMPT


def test_quiz_prompt_builder_switches_by_question_type():
    mcq_prompt = build_quiz_generation_prompt("mcq", 3, "medium", "חומר לימוד")
    open_prompt = build_quiz_generation_prompt("open", 3, "medium", "חומר לימוד")
    assert '"type":"mcq"' in mcq_prompt
    assert '"type":"open"' in open_prompt
    assert QUIZ_GENERATOR_SYSTEM_PROMPT


def test_grading_prompt_builder_contains_semantic_schema():
    prompt = build_semantic_grading_prompt("מהי למידת מכונה?", "הסבר על למידה מנתונים", "מודל שלומד מנתונים")
    assert "accepted_semantically" in prompt
    assert "score_0_to_100" in prompt
    assert QUIZ_GRADER_SYSTEM_PROMPT
