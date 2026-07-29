from app.prompts.grading import QUIZ_GRADER_SYSTEM_PROMPT, build_semantic_grading_prompt
from app.prompts.group_peers import (
    INTERMEDIATE_PEER_SYSTEM_PROMPT,
    NOVICE_PEER_SYSTEM_PROMPT,
    build_group_peer_user_prompt,
)
from app.prompts.podcast import PODCAST_SYSTEM_PROMPT, build_podcast_user_prompt
from app.prompts.project_ideas import PROJECT_IDEAS_SYSTEM_PROMPT, build_project_ideas_user_prompt
from app.prompts.quiz import QUIZ_GENERATOR_SYSTEM_PROMPT, build_quiz_generation_prompt
from app.prompts.teacher import TEACHER_SYSTEM_PROMPT, build_teacher_user_prompt

__all__ = [
    "INTERMEDIATE_PEER_SYSTEM_PROMPT",
    "NOVICE_PEER_SYSTEM_PROMPT",
    "PODCAST_SYSTEM_PROMPT",
    "PROJECT_IDEAS_SYSTEM_PROMPT",
    "QUIZ_GENERATOR_SYSTEM_PROMPT",
    "QUIZ_GRADER_SYSTEM_PROMPT",
    "TEACHER_SYSTEM_PROMPT",
    "build_group_peer_user_prompt",
    "build_podcast_user_prompt",
    "build_project_ideas_user_prompt",
    "build_quiz_generation_prompt",
    "build_semantic_grading_prompt",
    "build_teacher_user_prompt",
]
