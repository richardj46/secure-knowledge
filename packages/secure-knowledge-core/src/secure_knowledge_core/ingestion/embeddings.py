import math
from typing import Protocol

from google import genai
from google.genai import types

from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.ingestion.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class GeminiEmbeddingProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise EmbeddingConfigurationError("GEMINI_API_KEY is required.")

        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.dimensions,
                ),
            )
        except Exception:
            # Provider responses may contain request details. Keep them out of
            # persisted errors and exception chains surfaced by the worker.
            raise EmbeddingProviderError from None
        embeddings = response.embeddings or []
        vectors = [list(embedding.values or []) for embedding in embeddings]

        if len(vectors) != len(texts):
            raise EmbeddingProviderError

        if any(len(vector) != self.dimensions for vector in vectors):
            raise EmbeddingProviderError

        return [self._normalize(vector) for vector in vectors]

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            raise EmbeddingProviderError
        return [value / magnitude for value in vector]
