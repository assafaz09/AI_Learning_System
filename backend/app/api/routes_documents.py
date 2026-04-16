import re
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from httpx import Timeout, get
from pypdf import PdfReader
from sqlalchemy.orm import Session
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db import get_db
from app.models import Document, User, UserDocumentSelection
from app.schemas import DocumentOut, ExternalSourceImportRequest, SelectedDocumentsRequest, SelectedDocumentsResponse
from app.services.ai import ai_client
from app.services.vector_store import VectorStore


router = APIRouter(prefix="/documents", tags=["documents"])
vector_store = VectorStore()
supported_text_extensions = {".txt", ".md", ".csv", ".json"}


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    chunks = []
    for idx in range(0, len(text), chunk_size):
        chunks.append(text[idx : idx + chunk_size])
    return chunks or [text]


def sanitize_text(text: str) -> str:
    sanitized = text.replace("\x00", "")
    return "\n".join(line.strip() for line in sanitized.splitlines() if line.strip())


def _extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id or None
    if "youtube.com" in host:
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            video_id = query.get("v", [""])[0]
            return video_id or None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts"}:
            return parts[1]
    return None


def _extract_webpage_text(url: str) -> tuple[str, str]:
    response = get(url, timeout=Timeout(12.0))
    response.raise_for_status()
    html = response.text
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "Web Source"
    without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    no_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    text = sanitize_text(re.sub(r"\s+", " ", no_tags))
    if not text:
        raise HTTPException(status_code=400, detail="לא ניתן לחלץ טקסט מהעמוד")
    return title, text


def _download_youtube_audio(url: str, video_id: str) -> Path:
    target_template = str(Path(settings.upload_dir) / f"{video_id}_{uuid4()}.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": target_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = Path(ydl.prepare_filename(info))
    if not file_path.exists():
        raise RuntimeError("Failed to download YouTube audio")
    return file_path


def _extract_youtube_text(url: str) -> tuple[str, str, str]:
    video_id = _extract_youtube_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="קישור YouTube לא תקין")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["he", "en"])
        text = sanitize_text(" ".join(item.get("text", "") for item in transcript))
    except Exception as exc:
        audio_path: Path | None = None
        try:
            audio_path = _download_youtube_audio(url, video_id)
            text = sanitize_text(ai_client.transcribe_audio(audio_path))
        except Exception as fallback_exc:
            raise HTTPException(
                status_code=400,
                detail="לא ניתן לייבא את הסרטון מ-YouTube. אין כתוביות זמינות וגם תמלול האודיו נכשל.",
            ) from fallback_exc
        finally:
            if audio_path:
                try:
                    audio_path.unlink(missing_ok=True)
                except Exception:
                    pass
    if not text:
        raise HTTPException(status_code=400, detail="לא נמצא תמלול טקסטואלי בסרטון YouTube.")
    return f"YouTube:{video_id}", text, video_id


def index_document_chunks(user_id: int, document_id: int, content: str) -> int:
    indexed = 0
    for chunk in chunk_text(content):
        vector = ai_client.embed(chunk)
        vector_store.upsert_chunk(
            chunk_id=vector_store.new_chunk_id(),
            vector=vector,
            payload={"user_id": user_id, "document_id": document_id, "text": chunk},
        )
        indexed += 1
    return indexed


def extract_text_from_upload(file: UploadFile, content_bytes: bytes) -> str:
    filename = (file.filename or "").lower()
    is_pdf = filename.endswith(".pdf") or file.content_type == "application/pdf"
    if is_pdf:
        try:
            reader = PdfReader(BytesIO(content_bytes))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"לא ניתן לקרוא את קובץ ה-PDF: {exc}") from exc
        clean_text = sanitize_text(text)
        if not clean_text:
            raise HTTPException(status_code=400, detail="לא נמצא טקסט קריא בקובץ PDF")
        return clean_text

    extension = Path(filename).suffix
    if extension and extension not in supported_text_extensions:
        raise HTTPException(status_code=400, detail="סוג הקובץ אינו נתמך. ניתן להעלות PDF או קבצי טקסט")

    text = content_bytes.decode("utf-8", errors="ignore")
    clean_text = sanitize_text(text)
    if not clean_text:
        raise HTTPException(status_code=400, detail="הקובץ ריק או לא מכיל טקסט קריא")
    return clean_text


def _create_and_index_document(
    db: Session,
    user: User,
    name: str,
    content: str,
    path_value: str,
    source_type: str = "file",
    source_url: str | None = None,
    external_id: str | None = None,
) -> Document:
    doc = Document(
        user_id=user.id,
        name=name,
        content=content,
        path=path_value,
        source_type=source_type,
        source_url=source_url,
        external_id=external_id,
    )
    db.add(doc)
    db.flush()
    index_document_chunks(user.id, doc.id, content)
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        content_bytes = await file.read()
        content = extract_text_from_upload(file, content_bytes)

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid4()}_{file.filename}"
        full_path = upload_dir / file_name
        full_path.write_bytes(content_bytes)

        try:
            return _create_and_index_document(
                db,
                user,
                file.filename or "מסמך.txt",
                content,
                str(full_path),
                source_type="file",
            )
        except Exception as exc:
            db.rollback()
            try:
                full_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM/Embeddings: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בהעלאת המסמך: {exc}") from exc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc()).all()


@router.get("/selected", response_model=SelectedDocumentsResponse)
def get_selected_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    selected = (
        db.query(UserDocumentSelection.document_id)
        .filter(UserDocumentSelection.user_id == user.id)
        .all()
    )
    return SelectedDocumentsResponse(document_ids=[item[0] for item in selected])


@router.put("/selected", response_model=SelectedDocumentsResponse)
def set_selected_documents(
    payload: SelectedDocumentsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    requested_ids = list(dict.fromkeys(payload.document_ids))
    if not requested_ids:
        db.query(UserDocumentSelection).filter(UserDocumentSelection.user_id == user.id).delete(synchronize_session=False)
        db.commit()
        return SelectedDocumentsResponse(document_ids=[])

    valid_docs = (
        db.query(Document.id)
        .filter(Document.user_id == user.id, Document.id.in_(requested_ids))
        .all()
    )
    valid_ids = [item[0] for item in valid_docs]
    if len(valid_ids) != len(requested_ids):
        raise HTTPException(status_code=400, detail="נבחרו מסמכים שאינם שייכים למשתמש")

    db.query(UserDocumentSelection).filter(UserDocumentSelection.user_id == user.id).delete(synchronize_session=False)
    for document_id in valid_ids:
        db.add(UserDocumentSelection(user_id=user.id, document_id=document_id))
    db.commit()
    return SelectedDocumentsResponse(document_ids=valid_ids)


@router.post("/reindex")
def reindex_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    documents = db.query(Document).filter(Document.user_id == user.id).all()
    total_chunks = 0
    try:
        for doc in documents:
            total_chunks += index_document_chunks(user.id, doc.id, doc.content)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"שגיאת אינדוקס ל-Qdrant: {exc}") from exc
    return {"documents": len(documents), "chunks": total_chunks}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="המסמך לא נמצא")

    db.query(UserDocumentSelection).filter(
        UserDocumentSelection.user_id == user.id, UserDocumentSelection.document_id == document_id
    ).delete(synchronize_session=False)
    db.delete(document)
    db.commit()

    try:
        Path(document.path).unlink(missing_ok=True)
    except Exception:
        pass


@router.post("/import-url", response_model=DocumentOut)
def import_external_source(
    payload: ExternalSourceImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = str(payload.url)
    try:
        if "youtu" in url.lower():
            name, content, external_id = _extract_youtube_text(url)
            source_type = "youtube"
        else:
            name, content = _extract_webpage_text(url)
            external_id = None
            source_type = "web"
        return _create_and_index_document(
            db,
            user,
            name=name,
            content=content,
            path_value=f"external:{url}",
            source_type=source_type,
            source_url=url,
            external_id=external_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בייבוא מקור חיצוני: {exc}") from exc
