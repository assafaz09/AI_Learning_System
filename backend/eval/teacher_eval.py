"""Minimal teacher-agent eval: dataset + stub vector search (no Qdrant)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.graphs.teacher import invoke_teacher_chat
from app.agents.state import AgentGraphState

DEFAULT_CASES_PATH = Path(__file__).resolve().parent / "data" / "teacher_cases.json"


@dataclass
class TeacherEvalCase:
    id: str
    user_id: int
    document_ids: list[int]
    user_message: str
    context_chunks: list[str]


class StubTeacherVectorStore:
    """Returns fixed chunks for any search; use in eval without Qdrant."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = list(chunks)

    def search(
        self,
        vector: list[float],
        user_id: int,
        document_ids: list[int],
        limit: int = 5,
    ) -> list[str]:
        _ = (vector, user_id, document_ids)
        return self._chunks[:limit]


def load_teacher_cases(path: Path | None = None) -> list[TeacherEvalCase]:
    p = path or DEFAULT_CASES_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    out: list[TeacherEvalCase] = []
    for row in raw:
        out.append(
            TeacherEvalCase(
                id=str(row["id"]),
                user_id=int(row["user_id"]),
                document_ids=[int(x) for x in row["document_ids"]],
                user_message=str(row["user_message"]),
                context_chunks=[str(c) for c in row.get("context_chunks") or []],
            )
        )
    return out


def run_teacher_case(case: TeacherEvalCase) -> AgentGraphState:
    vs = StubTeacherVectorStore(case.context_chunks)
    state: AgentGraphState = {
        "user_id": case.user_id,
        "document_ids": case.document_ids,
        "user_message": case.user_message,
    }
    return invoke_teacher_chat(vs, state)


def summarize_teacher_result(case_id: str, out: AgentGraphState) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "has_llm_output": bool((out.get("llm_output") or "").strip()),
        "retrieved_n": len(out.get("retrieved_chunks") or []),
        "error_detail": (out.get("error_detail") or "")[:200],
        "llm_preview": ((out.get("llm_output") or "")[:160] + "…")
        if len(out.get("llm_output") or "") > 160
        else (out.get("llm_output") or ""),
    }
