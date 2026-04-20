import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.context import correlation_id_ctx
from app.agents.tracing import configure_langsmith
from app.core.config import settings

configure_langsmith()

from app.api.routes_auth import router as auth_router
from app.api.routes_documents import router as documents_router
from app.api.routes_grading import router as grading_router
from app.api.routes_history import router as history_router
from app.api.routes_podcast import router as podcast_router
from app.api.routes_quiz import router as quiz_router
from app.api.routes_teacher import router as teacher_router
from app.db import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Learning System API", version="0.1.0")


@app.middleware("http")
async def correlation_middleware(request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = correlation_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        correlation_id_ctx.reset(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(teacher_router)
app.include_router(quiz_router)
app.include_router(grading_router)
app.include_router(history_router)
app.include_router(podcast_router)
