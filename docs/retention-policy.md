# Data retention policy

SecureKnowledge removes detailed operational traces through explicit Celery Beat
jobs. Request handlers never delete traces as a side effect. Cleanup is permanent,
so deployments should configure backups and any legal hold before enabling the
schedule.

## Default periods

| Data | Setting | Default | Cleanup behavior |
| --- | --- | ---: | --- |
| Retrieval traces | `RETRIEVAL_TRACE_RETENTION_DAYS` | 90 days | Deletes ranked result details. A retrieval-run summary remains while a retained answer run references it. |
| Answer traces | `ANSWER_TRACE_RETENTION_DAYS` | 180 days | Deletes answer runs and their citations/reviews. Conversation messages remain, with their answer-run link cleared. |
| Audit events | `AUDIT_EVENT_RETENTION_DAYS` | 365 days | Deletes expired audit events using the organization-specific period when configured. |
| Evaluation details | `EVALUATION_RESULT_RETENTION_DAYS` | 365 days | Deletes case results and dependent case metrics, grader results, reviews, and evaluation-only conversations. |

Evaluation run summaries and run-level metrics are preserved. Daily organization
metrics are also preserved by every cleanup task. Daily aggregation runs before
the cleanup schedule.

## Organization-specific audit retention

Audit requirements vary by organization. Override the default with a JSON map:

```env
AUDIT_EVENT_RETENTION_OVERRIDES={"00000000-0000-0000-0000-000000000001":730}
```

Keys must be organization UUIDs and values must be positive day counts. Review
this setting with the organization's compliance owner. Increasing a period does
not restore events that have already been deleted.

## Schedule and operations

The worker schedules cleanup daily after the previous day's aggregate metrics:

1. `cleanup_expired_answer_traces` at 02:00 UTC
2. `cleanup_expired_retrieval_traces` at 02:15 UTC
3. `cleanup_expired_evaluation_details` at 02:30 UTC
4. `cleanup_expired_audit_events` at 02:45 UTC

Every cleanup emits a structured success or failure event with the cutoff and
deleted row counts. On first deployment, existing rows older than the configured
period are immediately eligible at the next scheduled run. Operators should
review the configured policy before starting Celery Beat.
