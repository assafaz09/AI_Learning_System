from __future__ import annotations

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from app.core.config import settings


class VectorStore:
    def __init__(self) -> None:
        self.memory_chunks: list[dict] = []
        self.enabled = True
        self.collection = settings.qdrant_collection_name
        self.vector_size: int | None = None
        try:
            api_key = settings.qdrant_api_key or None
            self.client = QdrantClient(url=settings.qdrant_url, api_key=api_key)
        except Exception:
            self.enabled = False
            self.client = None

    def _ensure_collection(self, vector_size: int) -> None:
        collections = {item.name for item in self.client.get_collections().collections}
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            self.vector_size = vector_size
        collection_info = self.client.get_collection(self.collection)
        current_size = collection_info.config.params.vectors.size
        self.vector_size = int(current_size)
        if self.vector_size != vector_size:
            raise ValueError("Qdrant vector size mismatch for current collection")
        self._ensure_payload_indexes(collection_info.payload_schema or {})

    def _ensure_payload_indexes(self, payload_schema: dict) -> None:
        required_integer_indexes = ("user_id", "document_id")
        for field in required_integer_indexes:
            if field in payload_schema:
                continue
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name=field,
                field_schema=PayloadSchemaType.INTEGER,
            )

    def new_chunk_id(self) -> str:
        return str(uuid4())

    def upsert_chunk(self, chunk_id: str, vector: list[float], payload: dict) -> None:
        if not self.enabled:
            self.vector_size = len(vector)
            self.memory_chunks.append({"id": chunk_id, "vector": vector, "payload": payload})
            return
        self._ensure_collection(len(vector))
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
        )

    def search(self, vector: list[float], user_id: int, document_ids: list[int], limit: int = 5) -> list[str]:
        if not document_ids:
            return []
        if not self.enabled:
            texts = [
                str(chunk["payload"].get("text", ""))
                for chunk in self.memory_chunks
                if chunk["payload"].get("user_id") == user_id
                and chunk["payload"].get("document_id") in document_ids
            ]
            return texts[:limit]
        self._ensure_collection(len(vector))
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter={
                "must": [
                    {"key": "user_id", "match": {"value": user_id}},
                    {"key": "document_id", "match": {"any": document_ids}},
                ]
            },
            limit=limit,
        )
        return [str(hit.payload.get("text", "")) for hit in hits]
