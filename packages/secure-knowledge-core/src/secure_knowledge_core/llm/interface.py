from typing import Protocol

from secure_knowledge_core.llm.context import ContextPassage
from secure_knowledge_core.llm.schemas import GeneratedAnswer


class AnswerProvider(Protocol):
    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> GeneratedAnswer:
        ...
