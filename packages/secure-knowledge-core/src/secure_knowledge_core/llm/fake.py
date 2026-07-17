from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import GeneratedAnswer
from secure_knowledge_core.llm.interface import AnswerProviderResult, ModelUsage


class FakeAnswerProvider:
    provider = "fake"

    def __init__(
        self,
        generated_answer: GeneratedAnswer,
    ) -> None:
        self.generated_answer = generated_answer
        self.received_question: str | None = None
        self.received_context: list[ContextPassage] = []
        self.call_count = 0

    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> AnswerProviderResult:
        self.call_count += 1
        self.received_question = question
        self.received_context = list(context)

        return AnswerProviderResult(
            generated_answer=self.generated_answer,
            model_name="fake-answer-model",
            provider_request_id="fake-request-id",
            usage=ModelUsage(
                input_tokens=100,
                output_tokens=30,
                total_tokens=130,
            ),
        )
