from secure_knowledge_core.ingestion.embeddings import EmbeddingProvider


class QueryEmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider

    def create_query_embedding(self, query: str) -> list[float]:
        embeddings = self.provider.embed_texts([query])

        if len(embeddings) != 1:
            raise RuntimeError(
                "Embedding provider returned an unexpected result count."
            )

        return embeddings[0]
