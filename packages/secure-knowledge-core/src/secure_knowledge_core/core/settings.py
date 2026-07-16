from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "secure-knowledge-core"
    jwt_audience: str = "secure-knowledge-api"
    access_token_expire_minutes: int = 30

    redis_url: str = "redis://localhost:6379/0"

    object_storage_bucket: str = "secure-knowledge-documents"
    object_storage_endpoint_url: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_access_key: str
    object_storage_secret_key: str

    gemini_api_key: str | None = None
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536

    max_upload_size_bytes: int = 20 * 1024 * 1024
    ingestion_lease_seconds: int = 15 * 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
