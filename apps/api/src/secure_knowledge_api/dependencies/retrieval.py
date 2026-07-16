from typing import Annotated

from fastapi import Depends, HTTPException, status

from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.ingestion.embeddings import GeminiEmbeddingProvider
from secure_knowledge_core.ingestion.exceptions import EmbeddingConfigurationError
from secure_knowledge_core.retrieval.service import RetrievalService


def get_retrieval_service(session: DatabaseSession) -> RetrievalService:
    try:
        embedding_provider = GeminiEmbeddingProvider()
    except EmbeddingConfigurationError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Retrieval is temporarily unavailable.",
        ) from exc

    return RetrievalService(
        session=session,
        embedding_provider=embedding_provider,
    )


RetrievalServiceDependency = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]
