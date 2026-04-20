from __future__ import annotations

import json

from app.agents.state import AgentGraphState


def podcast_parse_script(state: AgentGraphState) -> dict:
    raw = state.get("script_json") or ""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    retries = int(state.get("retry_count") or 0)
    try:
        lines = json.loads(cleaned)
        if not isinstance(lines, list) or len(lines) < 5:
            raise ValueError("Script too short or not a list")
        for item in lines:
            if item.get("speaker") not in ("A", "B") or not item.get("text"):
                raise ValueError(f"Invalid script line: {item}")
        return {"script_lines": lines, "selected_tool": "llm_chat"}
    except (json.JSONDecodeError, ValueError):
        return {"script_lines": [], "retry_count": retries + 1, "errors": ["podcast_script_parse_failed"]}
