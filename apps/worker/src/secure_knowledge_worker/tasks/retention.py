from collections.abc import Callable
from typing import Any

from secure_knowledge_core.core.logging import get_logger
from secure_knowledge_core.database.session import SessionFactory
from secure_knowledge_core.retention import (
    RetentionCleanupResult,
    RetentionService,
)
from secure_knowledge_worker.celery_app import celery_app

logger = get_logger(__name__)


def _run_cleanup(
    *,
    cleanup_name: str,
    cleanup: Callable[[RetentionService], RetentionCleanupResult],
) -> dict[str, Any]:
    with SessionFactory() as session:
        try:
            result = cleanup(RetentionService(session))
            session.commit()
        except Exception:
            session.rollback()
            logger.exception(
                "retention.cleanup_failed",
                extra={
                    "event": "retention.cleanup_failed",
                    "cleanup_name": cleanup_name,
                    "status": "failed",
                },
            )
            raise

    payload = {
        "cleanup_name": cleanup_name,
        "cutoff": result.cutoff.isoformat() if result.cutoff else None,
        "deleted_detail_rows": result.deleted_detail_rows,
        "deleted_summary_rows": result.deleted_summary_rows,
        "deleted_rows": result.deleted_rows,
    }
    logger.info(
        "retention.cleanup_completed",
        extra={
            "event": "retention.cleanup_completed",
            "status": "succeeded",
            **payload,
        },
    )
    return payload


@celery_app.task(
    name="secure_knowledge_worker.cleanup_expired_answer_traces"
)
def cleanup_expired_answer_traces() -> dict[str, Any]:
    return _run_cleanup(
        cleanup_name="answer_traces",
        cleanup=lambda service: service.cleanup_expired_answer_traces(),
    )


@celery_app.task(
    name="secure_knowledge_worker.cleanup_expired_retrieval_traces"
)
def cleanup_expired_retrieval_traces() -> dict[str, Any]:
    return _run_cleanup(
        cleanup_name="retrieval_traces",
        cleanup=lambda service: service.cleanup_expired_retrieval_traces(),
    )


@celery_app.task(
    name="secure_knowledge_worker.cleanup_expired_evaluation_details"
)
def cleanup_expired_evaluation_details() -> dict[str, Any]:
    return _run_cleanup(
        cleanup_name="evaluation_details",
        cleanup=lambda service: service.cleanup_expired_evaluation_details(),
    )


@celery_app.task(
    name="secure_knowledge_worker.cleanup_expired_audit_events"
)
def cleanup_expired_audit_events() -> dict[str, Any]:
    return _run_cleanup(
        cleanup_name="audit_events",
        cleanup=lambda service: service.cleanup_expired_audit_events(),
    )
