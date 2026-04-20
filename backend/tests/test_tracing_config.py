"""LangSmith env merge: LANGSMITH_* wizard vars sync to LANGCHAIN_* for the SDK."""

import os
from types import SimpleNamespace
from unittest.mock import patch

from app.agents import tracing as tracing_module


def test_configure_langsmith_merges_langsmith_prefixed_settings():
    fake = SimpleNamespace(
        langchain_tracing_v2=False,
        langsmith_tracing=True,
        langchain_api_key="",
        langsmith_api_key="ls-test-key",
        langchain_project="",
        langsmith_project="MyProject",
        langchain_endpoint="",
        langsmith_endpoint="https://api.smith.langchain.com",
        langchain_runs_batch_size="",
        langchain_metadata="",
    )
    old = {k: os.environ.pop(k, None) for k in (
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_TRACING",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_ENDPOINT",
        "LANGSMITH_ENDPOINT",
    )}
    try:
        with patch.object(tracing_module, "settings", fake):
            tracing_module.configure_langsmith()
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGSMITH_TRACING") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == "ls-test-key"
        assert os.environ.get("LANGSMITH_API_KEY") == "ls-test-key"
        assert os.environ.get("LANGCHAIN_PROJECT") == "MyProject"
        assert os.environ.get("LANGSMITH_PROJECT") == "MyProject"
    finally:
        for key, val in old.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
