from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.database.enums import Answerability


class FakeAnswerProvider:
    model = "fake-answer-provider-v1"

    def __init__(
        self,
        generated_answer: GeneratedAnswer | None = None,
    ) -> None:
        self.generated_answer = generated_answer

    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> GeneratedAnswer:
        del question
        if self.generated_answer is not None:
            return self.generated_answer

        if not context:
            return GeneratedAnswer(
                answer="I couldn't find sufficient supporting information.",
                answerability=Answerability.NOT_FOUND,
                confidence=1.0,
                citations=[],
                limitations=["No approved context was supplied."],
            )

        passage = context[0]
        return GeneratedAnswer(
            answer=passage.content,
            answerability=Answerability.ANSWERABLE,
            confidence=0.75,
            citations=[
                CitationDraft(
                    chunk_id=passage.chunk_id,
                    claims=[passage.content],
                )
            ],
            limitations=[],
        )
