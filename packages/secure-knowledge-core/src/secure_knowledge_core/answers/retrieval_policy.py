from secure_knowledge_core.retrieval.schemas import RetrievalResult


class RetrievalSufficiencyPolicy:
    def __init__(
        self,
        *,
        minimum_results: int = 1,
        minimum_top_score: float = 0.0,
    ) -> None:
        self.minimum_results = minimum_results
        self.minimum_top_score = minimum_top_score

    def is_sufficient(
        self,
        results: list[RetrievalResult],
    ) -> bool:
        if len(results) < self.minimum_results:
            return False

        if results[0].score < self.minimum_top_score:
            return False

        return True