from celery import Celery

from secure_knowledge_core.core.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "secure-knowledge-worker",
    broker=settings.redis_url,
    include=[
        "secure_knowledge_worker.jobs.outbox",
        "secure_knowledge_worker.tasks.ingestion",
    ],
)
celery_app.conf.beat_schedule = {
    "republish-pending-outbox-events": {
        "task": "secure_knowledge_worker.publish_pending_outbox_events",
        "schedule": 30.0,
    },
}
