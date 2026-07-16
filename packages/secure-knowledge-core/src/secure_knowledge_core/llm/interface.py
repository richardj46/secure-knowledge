from typing import Protocol

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import GeneratedAnswer


class AnswerProvider(Protocol):
    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> GeneratedAnswer:
        ...
