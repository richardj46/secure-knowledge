from enum import StrEnum


class AuditEventType(StrEnum):
    AUTH_USER_REGISTERED = "auth.user_registered"
    AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
    AUTH_LOGIN_FAILED = "auth.login_failed"

    ORGANIZATION_CREATED = "organization.created"
    ORGANIZATION_MEMBER_ADDED = "organization.member_added"
    ORGANIZATION_MEMBER_ROLE_CHANGED = "organization.member_role_changed"
    ORGANIZATION_MEMBER_REMOVED = "organization.member_removed"

    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_MEMBER_ADDED = "workspace.member_added"
    WORKSPACE_MEMBER_ROLE_CHANGED = "workspace.member_role_changed"
    WORKSPACE_MEMBER_REMOVED = "workspace.member_removed"

    GROUP_CREATED = "group.created"
    GROUP_MEMBER_ADDED = "group.member_added"
    GROUP_MEMBER_REMOVED = "group.member_removed"

    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_VISIBILITY_CHANGED = "document.visibility_changed"
    DOCUMENT_PERMISSION_USER_ADDED = "document.permission_user_added"
    DOCUMENT_PERMISSION_USER_REMOVED = "document.permission_user_removed"
    DOCUMENT_PERMISSION_GROUP_ADDED = "document.permission_group_added"
    DOCUMENT_PERMISSION_GROUP_REMOVED = "document.permission_group_removed"
    DOCUMENT_VERSION_UPLOADED = "document.version_uploaded"
    DOCUMENT_INGESTION_STARTED = "document.ingestion_started"
    DOCUMENT_INGESTION_SUCCEEDED = "document.ingestion_succeeded"
    DOCUMENT_INGESTION_FAILED = "document.ingestion_failed"
    DOCUMENT_INGESTION_RETRIED = "document.ingestion_retried"

    RETRIEVAL_EXECUTED = "retrieval.executed"

    ANSWER_GENERATED = "answer.generated"
    ANSWER_ABSTAINED = "answer.abstained"
    ANSWER_FAILED = "answer.failed"

    EVALUATION_RUN_STARTED = "evaluation.run_started"
    EVALUATION_RUN_COMPLETED = "evaluation.run_completed"
    EVALUATION_RUN_FAILED = "evaluation.run_failed"

    ADMIN_ANSWER_REVIEWED = "admin.answer_reviewed"
    ADMIN_EVALUATION_CASE_REVIEWED = "admin.evaluation_case_reviewed"


AUDIT_EVENT_TYPES = frozenset(event_type.value for event_type in AuditEventType)


def normalize_audit_event_type(value: str | AuditEventType) -> str:
    normalized = value.value if isinstance(value, AuditEventType) else value
    if normalized not in AUDIT_EVENT_TYPES:
        raise ValueError(f"Unsupported audit event type: {normalized!r}")
    return normalized
