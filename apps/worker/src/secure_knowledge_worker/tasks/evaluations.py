from uuid import UUID

from secure_knowledge_core.database.session import SessionFactory
from secure_knowledge_core.evaluations.exceptions import TransientEvaluationError
from secure_knowledge_core.evaluations.service import EvaluationService
from secure_knowledge_worker.celery_app import celery_app


@celery_app.task(
    name="secure_knowledge_worker.run_evaluation",
    bind=True,
    autoretry_for=(TransientEvaluationError,),
    retry_backoff=True,
    max_retries=3,
)
def run_evaluation(
    self,
    evaluation_run_id: str,
) -> None:
    with SessionFactory() as session:
        EvaluationService(session=session).execute_run(
            evaluation_run_id=UUID(evaluation_run_id)
        )
