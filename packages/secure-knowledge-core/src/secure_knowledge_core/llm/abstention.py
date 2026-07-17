from dataclasses import dataclass

from secure_knowledge_core.retrieval.schemas import RetrievalResult


@dataclass(frozen=True)
class AbstentionDecision:
    passages: list[RetrievalResult]
    reason: str | None = None

    @property
    def should_abstain(self) -> bool:
        return self.reason is not None


class AbstentionPolicy:
    def __init__(
        self,
        *,
        minimum_retrieval_score: float,
        minimum_vector_similarity: float,
        minimum_passage_characters: int,
    ) -> None:
        self.minimum_retrieval_score = minimum_retrieval_score
        self.minimum_vector_similarity = minimum_vector_similarity
        self.minimum_passage_characters = minimum_passage_characters

    def evaluate(
        self,
        results: list[RetrievalResult],
    ) -> AbstentionDecision:
        if not results:
            return AbstentionDecision(
                passages=[],
                reason="No supporting passages were retrieved.",
            )

        sufficiently_ranked = [
            result
            for result in results
            if result.score >= self.minimum_retrieval_score
        ]
        if not sufficiently_ranked:
            return AbstentionDecision(
                passages=[],
                reason="Retrieved passages were below the relevance threshold.",
            )

        substantial = [
            result
            for result in sufficiently_ranked
            if len(result.content.strip()) >= self.minimum_passage_characters
        ]
        if not substantial:
            return AbstentionDecision(
                passages=[],
                reason="Retrieved passages did not contain enough supporting text.",
            )

        related = [result for result in substantial if self._is_related(result)]
        if not related:
            return AbstentionDecision(
                passages=[],
                reason="Retrieved passages were too weak or unrelated.",
            )

        return AbstentionDecision(passages=related)

    def _is_related(self, result: RetrievalResult) -> bool:
        if result.keyword_rank is not None:
            return True
        return (
            result.vector_score is not None
            and result.vector_score >= self.minimum_vector_similarity
        )
