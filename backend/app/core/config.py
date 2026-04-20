from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ChatModelTask = Literal["teacher", "project_ideas", "quiz_generate", "quiz_grade", "podcast", "default"]


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql://postgres:postgres@postgres:5432/ai_learning"
    jwt_secret_key: str = "change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7
    jwt_refresh_cookie_name: str = "refresh_token"
    jwt_refresh_cookie_secure: bool = False
    jwt_refresh_cookie_samesite: str = "lax"
    cors_allow_origins: str = "http://localhost:3000"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    # Per-task chat models (optional). Empty = use openai_chat_model for that task.
    openai_model_teacher: str = ""
    openai_model_project_ideas: str = ""
    openai_model_quiz_generate: str = ""
    openai_model_quiz_grade: str = ""
    openai_model_podcast: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    whisper_mode: str = "local"  # "local" (free, slower) or "api" (paid, faster)
    whisper_local_model: str = "base"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "documents"
    upload_dir: str = "/app/uploads"
    next_public_api_base_url: str = "http://localhost:8000"

    # LangSmith / LangChain tracing (optional)
    # Use either LANGCHAIN_* (legacy) or LANGSMITH_* (LangSmith UI wizard) — both are merged at startup.
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "ai-learning-system"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_runs_batch_size: str = ""
    langchain_metadata: str = ""
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = ""
    langsmith_endpoint: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def resolve_chat_model(self, task: ChatModelTask = "default") -> str:
        per_task = {
            "teacher": self.openai_model_teacher,
            "project_ideas": self.openai_model_project_ideas,
            "quiz_generate": self.openai_model_quiz_generate,
            "quiz_grade": self.openai_model_quiz_grade,
            "podcast": self.openai_model_podcast,
            "default": "",
        }
        chosen = (per_task.get(task) or "").strip()
        return chosen or self.openai_chat_model


settings = Settings()
