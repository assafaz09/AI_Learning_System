from datetime import datetime

from pydantic import BaseModel, HttpUrl


class DocumentOut(BaseModel):
    id: int
    name: str
    source_type: str = "file"
    source_url: str | None = None
    external_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SelectedDocumentsRequest(BaseModel):
    document_ids: list[int]


class SelectedDocumentsResponse(BaseModel):
    document_ids: list[int]


class ExternalSourceImportRequest(BaseModel):
    url: HttpUrl
