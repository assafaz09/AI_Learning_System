from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_chat_model(*, streaming: bool = False, temperature: float = 0.2, **kwargs) -> ChatOpenAI:
    """LangChain chat model; tests may patch this function."""
    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key or None,
        temperature=temperature,
        streaming=streaming,
        **kwargs,
    )
