from __future__ import annotations

import io
import json
import logging
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.runnables import RunnableConfig
from pydub import AudioSegment
from sqlalchemy.orm import Session

from app.agents.graphs.podcast import invoke_podcast_script_pipeline
from app.agents.tracing import graph_run_metadata
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db import get_db
from app.models import Document, Podcast, User
from app.services.ai import ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/podcast", tags=["podcast"])

VOICE_MAP = {"A": "alloy", "B": "nova"}


def _fetch_documents_content(document_ids: list[int], user: User, db: Session) -> str:
    docs = (
        db.query(Document)
        .filter(Document.user_id == user.id, Document.id.in_(document_ids))
        .all()
    )
    if not docs:
        raise HTTPException(status_code=400, detail="לא נבחרו מסמכים תקינים")
    return "\n---\n".join(doc.content for doc in docs)


@router.post("/generate")
def generate_podcast(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document_ids = payload.get("document_ids", [])
    if not document_ids:
        raise HTTPException(status_code=400, detail="יש לבחור לפחות מסמך אחד")

    content = _fetch_documents_content(document_ids, user, db)

    podcast = Podcast(
        user_id=user.id,
        title=f"פודקאסט — {len(document_ids)} מסמכים",
        status="generating",
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    podcast_id = podcast.id

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream() -> Generator[str, None, None]:
        try:
            yield sse("progress", {"message": "כותב תסריט לפודקאסט..."})

            cfg = RunnableConfig(tags=["podcast", "script"], metadata=graph_run_metadata("podcast_script"))
            script_state = invoke_podcast_script_pipeline({"doc_content": content, "retry_count": 0}, config=cfg)
            script = script_state.get("script_lines") or []

            if not script:
                logger.warning("Script pipeline failed after retries: %s", script_state.get("errors"))
                yield sse("error", {"detail": "יצירת התסריט נכשלה, נסה שוב"})
                db.query(Podcast).filter(Podcast.id == podcast_id).update({"status": "failed"})
                db.commit()
                return

            total = len(script)
            yield sse("progress", {"message": f"ממיר {total} משפטים לאודיו..."})

            audio_chunks: list[bytes] = []
            for idx, line in enumerate(script):
                voice = VOICE_MAP.get(line["speaker"], "alloy")
                chunk_bytes = ai_client.text_to_speech(line["text"], voice=voice)
                audio_chunks.append(chunk_bytes)

                if (idx + 1) % 5 == 0 or idx == total - 1:
                    yield sse("progress", {
                        "message": f"ממיר לאודיו... ({idx + 1}/{total})",
                        "step": idx + 1,
                        "total": total,
                    })

            yield sse("progress", {"message": "מרכיב את הפודקאסט..."})

            combined = AudioSegment.empty()
            short_pause = AudioSegment.silent(duration=300)
            for chunk_bytes in audio_chunks:
                segment = AudioSegment.from_mp3(io.BytesIO(chunk_bytes))
                combined += segment + short_pause

            podcast_dir = Path(settings.upload_dir) / "podcasts"
            podcast_dir.mkdir(parents=True, exist_ok=True)
            filename = f"podcast_{podcast_id}_{uuid4().hex[:8]}.mp3"
            file_path = podcast_dir / filename
            combined.export(str(file_path), format="mp3", bitrate="128k")

            duration_ms = len(combined)
            duration = duration_ms / 1000.0
            if duration <= 0 and file_path.stat().st_size > 0:
                verified = AudioSegment.from_mp3(str(file_path))
                duration = len(verified) / 1000.0
            db.query(Podcast).filter(Podcast.id == podcast_id).update({
                "script": json.dumps(script, ensure_ascii=False),
                "audio_path": str(file_path),
                "duration_seconds": duration,
                "status": "done",
            })
            db.commit()

            yield sse("done", {"podcast_id": podcast_id, "duration_seconds": duration})

        except Exception as exc:
            logger.exception("Podcast generation failed")
            db.query(Podcast).filter(Podcast.id == podcast_id).update({"status": "failed"})
            db.commit()
            yield sse("error", {"detail": f"יצירת הפודקאסט נכשלה: {exc}"})

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/list")
def list_podcasts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    podcasts = (
        db.query(Podcast)
        .filter(Podcast.user_id == user.id, Podcast.status == "done")
        .order_by(Podcast.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "duration_seconds": p.duration_seconds,
            "created_at": p.created_at.isoformat(),
        }
        for p in podcasts
    ]


@router.get("/{podcast_id}/audio")
def get_podcast_audio(podcast_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    podcast = (
        db.query(Podcast)
        .filter(Podcast.id == podcast_id, Podcast.user_id == user.id)
        .first()
    )
    if not podcast or podcast.status != "done":
        raise HTTPException(status_code=404, detail="הפודקאסט לא נמצא")

    audio_path = Path(podcast.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="קובץ האודיו לא נמצא")

    return FileResponse(str(audio_path), media_type="audio/mpeg", filename=f"{podcast.title}.mp3")
