from celery import Celery
from celery.schedules import crontab

from secure_knowledge_core.core.logging import configure_logging
from secure_knowledge_core.core.settings import get_settings

settings = get_settings()
configure_logging(service="worker", settings=settings)

celery_app = Celery(
    "secure-knowledge-worker",
    broker=settings.redis_url,
    include=[
        "secure_knowledge_worker.jobs.outbox",
        "secure_knowledge_worker.tasks.evaluations",
        "secure_knowledge_worker.tasks.ingestion",
        "secure_knowledge_worker.tasks.metrics",
        "secure_knowledge_worker.tasks.retention",
    ],
)
celery_app.conf.beat_schedule = {
    "republish-pending-outbox-events": {
        "task": "secure_knowledge_worker.publish_pending_outbox_events",
        "schedule": 30.0,
    },
    "aggregate-daily-organization-metrics": {
        "task": "secure_knowledge_worker.aggregate_daily_organization_metrics",
        "schedule": crontab(hour=0, minute=15),
    },
    "cleanup-expired-answer-traces": {
        "task": "secure_knowledge_worker.cleanup_expired_answer_traces",
        "schedule": crontab(hour=2, minute=0),
    },
    "cleanup-expired-retrieval-traces": {
        "task": "secure_knowledge_worker.cleanup_expired_retrieval_traces",
        "schedule": crontab(hour=2, minute=15),
    },
    "cleanup-expired-evaluation-details": {
        "task": "secure_knowledge_worker.cleanup_expired_evaluation_details",
        "schedule": crontab(hour=2, minute=30),
    },
    "cleanup-expired-audit-events": {
        "task": "secure_knowledge_worker.cleanup_expired_audit_events",
        "schedule": crontab(hour=2, minute=45),
    },
}
celery_app.conf.worker_hijack_root_logger = False
