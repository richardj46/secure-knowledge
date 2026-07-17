from datetime import UTC, date, datetime, timedelta

from secure_knowledge_core.database.session import SessionFactory
from secure_knowledge_core.metrics.daily import DailyMetricAggregationService
from secure_knowledge_worker.celery_app import celery_app


@celery_app.task(
    name="secure_knowledge_worker.aggregate_daily_organization_metrics"
)
def aggregate_daily_organization_metrics(
    metric_date: str | None = None,
) -> int:
    target_date = (
        date.fromisoformat(metric_date)
        if metric_date is not None
        else datetime.now(UTC).date() - timedelta(days=1)
    )
    with SessionFactory() as session:
        try:
            count = DailyMetricAggregationService(session).rebuild_date(
                metric_date=target_date
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    return count
