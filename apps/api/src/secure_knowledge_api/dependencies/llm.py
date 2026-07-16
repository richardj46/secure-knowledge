from typing import Annotated

from fastapi import Depends

from secure_knowledge_core.llm.fake import FakeAnswerProvider
from secure_knowledge_core.llm.interface import AnswerProvider


def get_answer_provider() -> AnswerProvider:
    return FakeAnswerProvider()


AnswerProviderDependency = Annotated[
    AnswerProvider,
    Depends(get_answer_provider),
]
