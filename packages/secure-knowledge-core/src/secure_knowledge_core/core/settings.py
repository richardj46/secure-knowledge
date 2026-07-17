from functools import lru_cache
from uuid import UUID

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = True
    log_sensitive_content: bool = False

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
    answer_model: str = "gemini-2.5-flash"
    answer_model_timeout_seconds: float = 45.0
    answer_model_max_retries: int = 2
    answer_max_context_chunks: int = 10
    answer_max_context_tokens: int = 10_000
    answer_minimum_retrieval_score: float = 0.015
    answer_minimum_vector_similarity: float = 0.55
    answer_minimum_passage_characters: int = 40
    answer_retrieval_limit: int = 10
    reranker_model: str | None = None

    evaluation_live_maximum_cases: int = 25

    retrieval_trace_retention_days: int = Field(default=90, ge=1)
    answer_trace_retention_days: int = Field(default=180, ge=1)
    audit_event_retention_days: int = Field(default=365, ge=1)
    evaluation_result_retention_days: int = Field(default=365, ge=1)
    audit_event_retention_overrides: dict[str, int] = Field(
        default_factory=dict,
    )

    max_upload_size_bytes: int = 20 * 1024 * 1024
    ingestion_lease_seconds: int = 15 * 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("audit_event_retention_overrides")
    @classmethod
    def validate_audit_event_retention_overrides(
        cls,
        value: dict[str, int],
    ) -> dict[str, int]:
        for organization_id, retention_days in value.items():
            UUID(organization_id)
            if retention_days < 1:
                raise ValueError(
                    "Audit event retention overrides must be at least one day."
                )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
