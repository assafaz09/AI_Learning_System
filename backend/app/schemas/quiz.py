from pydantic import BaseModel


class QuizGenerateRequest(BaseModel):
    document_ids: list[int]
    difficulty: str = "medium"
    question_count: int = 5
    question_type: str = "open"


class QuestionOut(BaseModel):
    id: int
    prompt: str
    question_type: str = "open"
    options: list[str] = []

    class Config:
        from_attributes = True


class QuizOut(BaseModel):
    id: int
    title: str
    questions: list[QuestionOut]

    class Config:
        from_attributes = True


class QuizSubmitRequest(BaseModel):
    answers: dict[int, str]


class GradeOut(BaseModel):
    score: float
    feedback: str
    feedback_items: list[dict] = []
