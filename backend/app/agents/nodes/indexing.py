from __future__ import annotations

from app.agents.state import AgentGraphState
from app.services.ai import ai_client
from app.services.vector_store import VectorStore


def _chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    chunks: list[str] = []
    for idx in range(0, len(text), chunk_size):
        chunks.append(text[idx : idx + chunk_size])
    return chunks or [text]


def index_document_content(state: AgentGraphState, vector_store: VectorStore) -> dict:
    user_id = int(state["index_user_id"])
    document_id = int(state["index_document_id"])
    content = state.get("index_content") or ""
    indexed = 0
    for chunk in _chunk_text(content):
        vector = ai_client.embed(chunk)
        vector_store.upsert_chunk(
            chunk_id=vector_store.new_chunk_id(),
            vector=vector,
            payload={"user_id": user_id, "document_id": document_id, "text": chunk},
        )
        indexed += 1
    return {"chunks_indexed": indexed, "selected_tool": "ingest"}
