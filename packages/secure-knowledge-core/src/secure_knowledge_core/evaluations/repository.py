from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.database.models import EvaluationGraderResult
from secure_knowledge_core.evaluations.graders.citations import (
    CitationCorrectnessResult,
)


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_citation_correctness_grades(
        self,
        *,
        evaluation_run_id: UUID,
        evaluation_case_result_id: UUID,
        result: CitationCorrectnessResult,
    ) -> list[EvaluationGraderResult]:
        records = [
            EvaluationGraderResult(
                evaluation_run_id=evaluation_run_id,
                evaluation_case_result_id=evaluation_case_result_id,
                grader_name="citation-correctness",
                grader_version="v1",
                claim_index=item.claim_index,
                claim=item.claim,
                score=item.grade.score,
                passed=item.grade.supported,
                explanation=item.grade.explanation,
                details={"supported": item.grade.supported},
            )
            for item in result.claim_grades
        ]
        self.session.add_all(records)
        return records
