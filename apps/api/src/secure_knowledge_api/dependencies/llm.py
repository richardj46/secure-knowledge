from typing import Annotated

from fastapi import Depends, HTTPException, status

from secure_knowledge_core.llm.exceptions import LLMProviderConfigurationError
from secure_knowledge_core.llm.gemini_provider import GeminiAnswerProvider
from secure_knowledge_core.llm.interface import AnswerProvider


def get_answer_provider() -> AnswerProvider:
    try:
        return GeminiAnswerProvider()
    except LLMProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Answer generation is temporarily unavailable.",
        ) from exc


AnswerProviderDependency = Annotated[
    AnswerProvider,
    Depends(get_answer_provider),
]
