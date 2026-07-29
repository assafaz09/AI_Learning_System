from pydantic import BaseModel, Field, field_validator


class GroupLearningSessionCreate(BaseModel):
    document_ids: list[int] = Field(..., min_length=1)
    title: str | None = None

    @field_validator("document_ids")
    @classmethod
    def ids_positive(cls, v: list[int]) -> list[int]:
        if any(i <= 0 for i in v):
            raise ValueError("מזהי מסמכים חייבים להיות חיוביים")
        return v

    @field_validator("title")
    @classmethod
    def title_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class GroupLearningSessionOut(BaseModel):
    id: int
    title: str
    document_ids: list[int]
    next_speaker: str


class GroupLearningPostMessage(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("יש להזין הודעה")
        return s


class GroupLearningReplyOut(BaseModel):
    session_id: int
    reply: str
    speaker: str


class GroupLearningMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class GroupLearningMessagesResponse(BaseModel):
    session_id: int
    messages: list[GroupLearningMessageOut]
