from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db import get_db
from app.models import Document, User, UserDocumentSelection
from app.schemas import DocumentOut, SelectedDocumentsRequest, SelectedDocumentsResponse
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

        doc = Document(user_id=user.id, name=file.filename or "מסמך.txt", content=content, path=str(full_path))
        db.add(doc)
        db.flush()

        try:
            index_document_chunks(user.id, doc.id, content)
        except Exception as exc:
            db.rollback()
            try:
                full_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=503, detail=f"שגיאת חיבור ל-LLM/Embeddings: {exc}") from exc

        db.commit()
        db.refresh(doc)
        return doc
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
