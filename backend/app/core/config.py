from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql://postgres:postgres@postgres:5432/ai_learning"
    jwt_secret_key: str = "change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "documents"
    upload_dir: str = "/app/uploads"
    next_public_api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
