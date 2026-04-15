from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class AIClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key)
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None

    def _require_client(self) -> OpenAI:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is missing or empty")
        return self.client

    def embed(self, text: str) -> list[float]:
        client = self._require_client()
        response = client.embeddings.create(model=settings.openai_embedding_model, input=text)
        return response.data[0].embedding

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        client = self._require_client()
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


ai_client = AIClient()
