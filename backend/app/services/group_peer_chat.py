from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.llm import get_chat_model
from app.models import GroupLearningMessage, GroupLearningSession
from app.prompts.group_peers import (
    INTERMEDIATE_PEER_SYSTEM_PROMPT,
    NOVICE_PEER_SYSTEM_PROMPT,
    build_group_peer_user_prompt,
)
from app.services.ai import ai_client
from app.services.vector_store import VectorStore

PeerSpeaker = Literal["novice", "intermediate"]

_OTHER_SPEAKER: dict[PeerSpeaker, PeerSpeaker] = {"novice": "intermediate", "intermediate": "novice"}


def _speaker_label(role: str) -> str:
    if role == "novice":
        return "סוכן מתחיל"
    if role == "intermediate":
        return "סוכן בינוני"
    return "משתמש"


def build_history_transcript(prior_messages: list[GroupLearningMessage]) -> str:
    lines: list[str] = []
    for m in prior_messages:
        lines.append(f"{_speaker_label(m.role)}: {m.content}")
    return "\n".join(lines)


def retrieve_peer_contexts(
    vector_store: VectorStore,
    *,
    user_id: int,
    document_ids: list[int],
    user_message: str,
    limit: int = 5,
) -> list[str]:
    user_vector = ai_client.embed(user_message)
    return vector_store.search(user_vector, user_id=user_id, document_ids=document_ids, limit=limit)


def peer_system_for(speaker: PeerSpeaker) -> str:
    return NOVICE_PEER_SYSTEM_PROMPT if speaker == "novice" else INTERMEDIATE_PEER_SYSTEM_PROMPT


def chat_task_for(speaker: PeerSpeaker) -> str:
    return "group_peer_novice" if speaker == "novice" else "group_peer_intermediate"


def run_group_peer_turn(
    db: Session,
    vector_store: VectorStore,
    session: GroupLearningSession,
    user_message: str,
    *,
    config: RunnableConfig | None = None,
) -> tuple[str, PeerSpeaker]:
    """Persist user message, invoke LLM as current peer, persist reply, flip next_speaker. Returns (reply_text, speaker)."""
    doc_ids: list[int] = json.loads(session.document_ids_json)
    contexts = retrieve_peer_contexts(
        vector_store, user_id=session.user_id, document_ids=doc_ids, user_message=user_message
    )
    if not contexts:
        raise ValueError("לא נמצאו מקטעים רלוונטיים למסמכים שנבחרו. ודא שהחומר אוּנדקס.")

    speaker: PeerSpeaker = "intermediate" if session.next_speaker == "intermediate" else "novice"

    prior = (
        db.query(GroupLearningMessage)
        .filter(GroupLearningMessage.session_id == session.id)
        .order_by(GroupLearningMessage.created_at.asc(), GroupLearningMessage.id.asc())
        .all()
    )
    history_text = build_history_transcript(prior)

    user_prompt = build_group_peer_user_prompt(user_message, contexts, history_text)
    llm = get_chat_model(task=chat_task_for(speaker), streaming=False, temperature=0.35)
    messages = [SystemMessage(content=peer_system_for(speaker)), HumanMessage(content=user_prompt)]
    msg = llm.invoke(messages, config=config) if config is not None else llm.invoke(messages)
    reply = (getattr(msg, "content", None) or "").strip() or "לא התקבלה תשובה מהמודל."

    db.add(GroupLearningMessage(session_id=session.id, role="user", content=user_message))
    db.add(GroupLearningMessage(session_id=session.id, role=speaker, content=reply))

    session.next_speaker = _OTHER_SPEAKER[speaker]
    db.add(session)
    db.commit()

    return reply, speaker
