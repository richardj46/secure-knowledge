from typing import Protocol

from secure_knowledge_core.answers.context import ContextPassage


class ContextSelectionError(Exception):
    pass


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        ...


class ContextSelector:
    def __init__(
        self,
        *,
        maximum_chunks: int,
        maximum_tokens: int,
        token_counter: TokenCounter,
    ) -> None:
        self.maximum_chunks = maximum_chunks
        self.maximum_tokens = maximum_tokens
        self.token_counter = token_counter

    def select(
        self,
        passages: list[ContextPassage],
    ) -> list[ContextPassage]:
        selected: list[ContextPassage] = []
        used_tokens = 0

        for passage in passages:
            if len(selected) >= self.maximum_chunks:
                break

            passage_tokens = self.token_counter.count(
                passage.content
            )

            if passage_tokens > self.maximum_tokens:
                continue

            if used_tokens + passage_tokens > self.maximum_tokens:
                break

            selected.append(passage)
            used_tokens += passage_tokens

        if not selected:
            raise ContextSelectionError(
                "No retrieved passages fit within the context budget."
            )

        return selected
