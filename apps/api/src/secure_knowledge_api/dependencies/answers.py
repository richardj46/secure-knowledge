from typing import Annotated

from fastapi import Depends

from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_api.dependencies.llm import get_answer_provider
from secure_knowledge_api.dependencies.retrieval import RetrievalServiceDependency
from secure_knowledge_core.answers.context_selection import ContextSelector
from secure_knowledge_core.answers.service import AnswerService
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.llm.interface import AnswerProvider
from secure_knowledge_core.llm.pricing import CostCalculator
from secure_knowledge_core.llm.tokens import TokenCounter


def get_context_selector() -> ContextSelector:
    settings = get_settings()
    return ContextSelector(
        maximum_chunks=settings.answer_max_context_chunks,
        maximum_tokens=settings.answer_max_context_tokens,
        token_counter=TokenCounter(settings.answer_model),
    )


ContextSelectorDependency = Annotated[
    ContextSelector,
    Depends(get_context_selector),
]


def get_cost_calculator() -> CostCalculator:
    return CostCalculator(prices={})


CostCalculatorDependency = Annotated[
    CostCalculator,
    Depends(get_cost_calculator),
]


def get_answer_service(
    session: DatabaseSession,
    answer_provider: Annotated[
        AnswerProvider,
        Depends(get_answer_provider),
    ],
    retrieval_service: RetrievalServiceDependency,
    context_selector: ContextSelectorDependency,
    cost_calculator: CostCalculatorDependency,
) -> AnswerService:
    return AnswerService(
        session=session,
        retrieval_service=retrieval_service,
        answer_provider=answer_provider,
        context_selector=context_selector,
        cost_calculator=cost_calculator,
    )


AnswerServiceDependency = Annotated[
    AnswerService,
    Depends(get_answer_service),
]
