from __future__ import annotations

import json
import os

from app.agents.context import correlation_id_ctx
from app.core.config import settings


def configure_langsmith() -> None:
    """Apply LangSmith-related environment variables from app settings.

    Called at process startup so LangChain/LangGraph runs pick up tracing config.
    Sets both LANGCHAIN_* and LANGSMITH_* so SDKs and the LangSmith UI wizard env names work.
    """
    trace_on = bool(settings.langchain_tracing_v2 or settings.langsmith_tracing)
    api_key = (settings.langchain_api_key or settings.langsmith_api_key or "").strip()
    project = (settings.langchain_project or settings.langsmith_project or "ai-learning-system").strip()
    endpoint = (
        settings.langchain_endpoint or settings.langsmith_endpoint or "https://api.smith.langchain.com"
    ).strip()

    if trace_on:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"
    else:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGSMITH_TRACING", None)

    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_API_KEY"] = api_key
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGSMITH_PROJECT"] = project
    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

    if settings.langchain_runs_batch_size:
        os.environ["LANGCHAIN_RUNS_BATCH_SIZE"] = settings.langchain_runs_batch_size
    if settings.langchain_metadata:
        os.environ["LANGCHAIN_METADATA"] = settings.langchain_metadata


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


def graph_run_metadata(workflow: str) -> dict:
    meta: dict = {"workflow": workflow}
    rid = get_correlation_id()
    if rid:
        meta["request_id"] = rid
    if settings.langchain_metadata:
        try:
            extra = json.loads(settings.langchain_metadata)
            if isinstance(extra, dict):
                meta.update(extra)
        except json.JSONDecodeError:
            meta["langchain_metadata_raw"] = settings.langchain_metadata
    return meta
