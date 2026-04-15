from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class SelectedDocumentsRequest(BaseModel):
    document_ids: list[int]


class SelectedDocumentsResponse(BaseModel):
    document_ids: list[int]
