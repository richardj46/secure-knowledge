from typing import Protocol
from uuid import UUID

EVALUATION_RUN_REQUESTED = "evaluation_run.requested"


class EvaluationTaskQueue(Protocol):
    def enqueue_evaluation_run(
        self,
        *,
        evaluation_run_id: UUID,
    ) -> None:
        ...
