from typing import Annotated

from fastapi import Depends

from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_api.dependencies.llm import get_answer_provider
from secure_knowledge_api.dependencies.retrieval import RetrievalServiceDependency
from secure_knowledge_core.answers.service import AnswerService
from secure_knowledge_core.llm.interface import AnswerProvider


def get_answer_service(
    session: DatabaseSession,
    answer_provider: Annotated[
        AnswerProvider,
        Depends(get_answer_provider),
    ],
    retrieval_service: RetrievalServiceDependency,
) -> AnswerService:
    return AnswerService(
        session=session,
        retrieval_service=retrieval_service,
        answer_provider=answer_provider,
    )


AnswerServiceDependency = Annotated[
    AnswerService,
    Depends(get_answer_service),
]
