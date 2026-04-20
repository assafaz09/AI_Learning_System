from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class TeacherChatRequest(BaseModel):
    message: str
    document_ids: list[int] | None = None
    conversation_id: int | None = None


class TeacherChatResponse(BaseModel):
    conversation_id: int
    answer: str
    from_cache: bool = False


class TeacherMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class TeacherConversationMessagesResponse(BaseModel):
    conversation_id: int
    messages: list[TeacherMessageOut]


ExperienceBand = Literal["beginner_short", "intermediate_days", "advanced_extended"]


class ProjectIdeasRequest(BaseModel):
    learning_focus: str
    experience_band: ExperienceBand
    document_ids: list[int] | None = None

    @field_validator("learning_focus")
    @classmethod
    def learning_focus_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("יש למלא במה תרצה להתמקד")
        return stripped


class ProjectIdeasResponse(BaseModel):
    suggestions: str


SavedProjectStatus = Literal["not_started", "in_progress", "done"]
ProjectImportance = Literal["low", "medium", "high"]
ProjectKind = Literal["ai", "manual"]


class SavedProjectCreateAI(BaseModel):
    kind: Literal["ai"] = "ai"
    title: str
    suggestions_body: str
    learning_focus: str
    experience_band: ExperienceBand
    document_ids: list[int]

    @field_validator("title", "suggestions_body", "learning_focus")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("שדה חובה")
        return stripped

    @field_validator("document_ids")
    @classmethod
    def document_ids_non_empty(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("יש לצרף לפחות מסמך אחד")
        return value


class SavedProjectCreateManual(BaseModel):
    kind: Literal["manual"] = "manual"
    title: str
    description: str
    importance: ProjectImportance = "medium"
    status: SavedProjectStatus = "not_started"

    @field_validator("title", "description")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("שדה חובה")
        return stripped


SavedProjectCreate = Annotated[
    Union[SavedProjectCreateAI, SavedProjectCreateManual], Field(discriminator="kind")
]


class SavedProjectUpdate(BaseModel):
    title: str | None = None
    status: SavedProjectStatus | None = None
    notes: str | None = None
    importance: ProjectImportance | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def title_if_set(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("כותרת לא יכולה להיות ריקה")
        return stripped

    @field_validator("description")
    @classmethod
    def description_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "SavedProjectUpdate":
        if all(
            x is None
            for x in (self.title, self.status, self.notes, self.importance, self.description)
        ):
            raise ValueError("יש לשלוח לפחות שדה אחד לעדכון")
        return self


class SavedProjectOut(BaseModel):
    id: int
    kind: ProjectKind
    title: str
    suggestions_body: str
    learning_focus: str
    experience_band: str
    document_ids: list[int]
    importance: str
    description: str | None
    status: str
    notes: str | None
    created_at: str
    updated_at: str
