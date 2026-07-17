from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import ValidationError

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.evaluations.datasets import (
    DatasetLoadError,
    load_jsonl_text,
)
from secure_knowledge_core.evaluations.exceptions import (
    EvaluationAccessDeniedError,
    EvaluationBaselineRunNotFoundError,
    EvaluationBaselineRunNotReadyError,
    EvaluationCaseResultNotFoundError,
    EvaluationCaseScopeError,
    EvaluationDatasetConflictError,
    EvaluationDatasetNotFoundError,
    EvaluationDatasetReleasedError,
    EvaluationLiveDatasetTooLargeError,
    EvaluationRunNotFoundError,
)
from secure_knowledge_core.evaluations.schemas import (
    EvaluationCaseImportRead,
    EvaluationCaseRead,
    EvaluationCaseResultRead,
    EvaluationCaseReviewRead,
    EvaluationDatasetCreate,
    EvaluationDatasetRead,
    EvaluationMetricResultRead,
    EvaluationRunCreate,
    EvaluationRunRead,
    HumanReviewUpdate,
)
from secure_knowledge_core.evaluations.service import EvaluationService

router = APIRouter(tags=["evaluations"])

MAXIMUM_DATASET_UPLOAD_BYTES = 5 * 1024 * 1024


def _raise_resource_not_found(
    exception: Exception,
) -> Never:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Evaluation resource not found.",
    ) from exception


@router.post(
    "/organizations/{organization_id}/evaluation-datasets",
    response_model=EvaluationDatasetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_dataset(
    organization_id: UUID,
    data: EvaluationDatasetCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationDatasetRead:
    try:
        dataset = EvaluationService(session=session).create_dataset(
            organization_id=organization_id,
            user_id=current_user.id,
            name=data.name,
            description=data.description,
            version=data.version,
        )
    except EvaluationAccessDeniedError as exc:
        _raise_resource_not_found(exc)
    except EvaluationDatasetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An evaluation dataset with this name and version already exists.",
        ) from exc

    return EvaluationDatasetRead.model_validate(dataset)


@router.post(
    "/evaluation-datasets/{dataset_id}/cases/import",
    response_model=EvaluationCaseImportRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_evaluation_cases(
    dataset_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    file: Annotated[UploadFile, File()],
) -> EvaluationCaseImportRead:
    content = await file.read(MAXIMUM_DATASET_UPLOAD_BYTES + 1)
    await file.close()

    if len(content) > MAXIMUM_DATASET_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Evaluation dataset upload is too large.",
        )

    try:
        text = content.decode("utf-8")
        definitions = load_jsonl_text(
            text,
            source=file.filename or "<upload>",
        )
        cases = EvaluationService(session=session).import_cases(
            dataset_id=dataset_id,
            user_id=current_user.id,
            definitions=definitions,
        )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Evaluation datasets must be UTF-8 encoded JSONL.",
        ) from exc
    except DatasetLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The evaluation dataset is invalid.",
        ) from exc
    except (EvaluationAccessDeniedError, EvaluationDatasetNotFoundError) as exc:
        _raise_resource_not_found(exc)
    except EvaluationDatasetReleasedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Released datasets cannot be changed; create a new version.",
        ) from exc
    except EvaluationDatasetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more evaluation case IDs already exist.",
        ) from exc
    except EvaluationCaseScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An evaluation case references a resource outside the dataset scope.",
        ) from exc

    return EvaluationCaseImportRead(imported_count=len(cases))


@router.get(
    "/evaluation-datasets/{dataset_id}",
    response_model=EvaluationDatasetRead,
)
def get_evaluation_dataset(
    dataset_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationDatasetRead:
    try:
        dataset = EvaluationService(session=session).get_dataset(
            dataset_id=dataset_id,
            user_id=current_user.id,
        )
    except (EvaluationAccessDeniedError, EvaluationDatasetNotFoundError) as exc:
        _raise_resource_not_found(exc)

    return EvaluationDatasetRead.model_validate(dataset)


@router.get(
    "/evaluation-datasets/{dataset_id}/cases",
    response_model=list[EvaluationCaseRead],
)
def list_evaluation_cases(
    dataset_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[EvaluationCaseRead]:
    try:
        cases = EvaluationService(session=session).list_cases(
            dataset_id=dataset_id,
            user_id=current_user.id,
        )
    except (EvaluationAccessDeniedError, EvaluationDatasetNotFoundError) as exc:
        _raise_resource_not_found(exc)

    return [EvaluationCaseRead.model_validate(case) for case in cases]


@router.post(
    "/evaluation-datasets/{dataset_id}/runs",
    response_model=EvaluationRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_evaluation_run(
    dataset_id: UUID,
    data: EvaluationRunCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationRunRead:
    try:
        run = EvaluationService(session=session).create_run(
            dataset_id=dataset_id,
            started_by_user_id=current_user.id,
            baseline_run_id=data.baseline_run_id,
            configuration=data.build_configuration(
                default_answer_model=get_settings().answer_model,
                default_embedding_model=get_settings().embedding_model,
            ),
            code_revision=data.code_revision,
        )
    except (EvaluationAccessDeniedError, EvaluationDatasetNotFoundError) as exc:
        _raise_resource_not_found(exc)
    except EvaluationBaselineRunNotFoundError as exc:
        _raise_resource_not_found(exc)
    except EvaluationBaselineRunNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The baseline evaluation run has not completed successfully.",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The evaluation run configuration is invalid.",
        ) from exc
    except EvaluationLiveDatasetTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The dataset is too large for a live evaluation run.",
        ) from exc

    return EvaluationRunRead.model_validate(run)


@router.get(
    "/evaluation-runs/{run_id}",
    response_model=EvaluationRunRead,
)
def get_evaluation_run(
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationRunRead:
    try:
        run = EvaluationService(session=session).get_run(
            evaluation_run_id=run_id,
            user_id=current_user.id,
        )
    except (EvaluationAccessDeniedError, EvaluationRunNotFoundError) as exc:
        _raise_resource_not_found(exc)

    return EvaluationRunRead.model_validate(run)


@router.get(
    "/evaluation-runs/{run_id}/results",
    response_model=list[EvaluationCaseResultRead],
)
def list_evaluation_results(
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[EvaluationCaseResultRead]:
    try:
        results = EvaluationService(session=session).list_results(
            evaluation_run_id=run_id,
            user_id=current_user.id,
        )
    except (EvaluationAccessDeniedError, EvaluationRunNotFoundError) as exc:
        _raise_resource_not_found(exc)

    return [EvaluationCaseResultRead.model_validate(result) for result in results]


@router.get(
    "/evaluation-runs/{run_id}/metrics",
    response_model=list[EvaluationMetricResultRead],
)
def list_evaluation_metrics(
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[EvaluationMetricResultRead]:
    try:
        metrics = EvaluationService(session=session).list_metrics(
            evaluation_run_id=run_id,
            user_id=current_user.id,
        )
    except (EvaluationAccessDeniedError, EvaluationRunNotFoundError) as exc:
        _raise_resource_not_found(exc)

    return [EvaluationMetricResultRead.model_validate(metric) for metric in metrics]


@router.get(
    "/evaluation-case-results/{case_result_id}/review",
    response_model=EvaluationCaseReviewRead,
)
def get_evaluation_case_review(
    case_result_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationCaseReviewRead:
    try:
        return EvaluationService(session=session).get_case_review(
            evaluation_case_result_id=case_result_id,
            user_id=current_user.id,
        )
    except (
        EvaluationAccessDeniedError,
        EvaluationCaseResultNotFoundError,
        EvaluationRunNotFoundError,
    ) as exc:
        _raise_resource_not_found(exc)


@router.patch(
    "/evaluation-case-results/{case_result_id}/human-review",
    response_model=EvaluationCaseReviewRead,
)
def update_evaluation_case_review(
    case_result_id: UUID,
    data: HumanReviewUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationCaseReviewRead:
    try:
        return EvaluationService(session=session).update_case_review(
            evaluation_case_result_id=case_result_id,
            user_id=current_user.id,
            review=data,
        )
    except (
        EvaluationAccessDeniedError,
        EvaluationCaseResultNotFoundError,
        EvaluationRunNotFoundError,
    ) as exc:
        _raise_resource_not_found(exc)
