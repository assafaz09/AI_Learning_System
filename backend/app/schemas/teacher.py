from pydantic import BaseModel


class TeacherChatRequest(BaseModel):
    message: str
    document_ids: list[int] | None = None
    conversation_id: int | None = None


class TeacherChatResponse(BaseModel):
    conversation_id: int
    answer: str
