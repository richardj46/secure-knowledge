from dataclasses import dataclass
from typing import Protocol

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import GeneratedAnswer


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class AnswerProviderResult:
    generated_answer: GeneratedAnswer
    model_name: str
    provider_request_id: str | None
    usage: ModelUsage | None


class AnswerProvider(Protocol):
    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> AnswerProviderResult:
        ...
