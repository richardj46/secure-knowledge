from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.audit.redaction import (
    redact_audit_details,
    redact_sensitive_text,
)
from secure_knowledge_core.database.models import AuditEvent


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        organization_id: UUID,
        event_type: str,
        resource_type: str,
        resource_id: UUID | None,
        actor_user_id: UUID | None,
        outcome: str,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=redact_audit_details(details or {}),
            occurred_at=datetime.now(UTC),
            outcome=outcome,
            failure_code=failure_code,
            failure_message=(
                redact_sensitive_text(failure_message)[:2000]
                if failure_message
                else None
            ),
        )

        self.session.add(event)
        return event
