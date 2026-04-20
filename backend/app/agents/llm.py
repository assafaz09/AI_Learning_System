from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import ChatModelTask, settings


def get_chat_model(
    *,
    task: ChatModelTask = "default",
    streaming: bool = False,
    temperature: float = 0.2,
    **kwargs,
) -> ChatOpenAI:
    """LangChain chat model; ``task`` selects OPENAI_MODEL_* from settings (fallback: OPENAI_CHAT_MODEL)."""
    return ChatOpenAI(
        model=settings.resolve_chat_model(task),
        api_key=settings.openai_api_key or None,
        temperature=temperature,
        streaming=streaming,
        **kwargs,
    )
