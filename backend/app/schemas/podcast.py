from datetime import datetime

from pydantic import BaseModel


class PodcastGenerateRequest(BaseModel):
    document_ids: list[int]


class PodcastOut(BaseModel):
    id: int
    title: str
    duration_seconds: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
