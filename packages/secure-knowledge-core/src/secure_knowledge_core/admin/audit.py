from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.admin.pagination import (
    Page,
    decode_datetime_cursor,
    encode_datetime_cursor,
)
from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.models import AuditEvent


class AuditEventRead(BaseModel):
    id: UUID
    event_type: str
    actor_user_id: UUID | None
    resource_type: str
    resource_id: UUID | None
    outcome: str
    details: dict[str, Any]
    request_id: str | None
    occurred_at: datetime


class AdminAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)

    def list_events(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        filter_actor_user_id: UUID | None,
        event_type: str | None,
        resource_type: str | None,
        resource_id: UUID | None,
        outcome: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        request_id: str | None,
        limit: int,
        cursor: str | None,
    ) -> Page[AuditEventRead]:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
        statement = select(AuditEvent).where(
            AuditEvent.organization_id == organization_id
        )
        if filter_actor_user_id is not None:
            statement = statement.where(
                AuditEvent.actor_user_id == filter_actor_user_id
            )
        if event_type is not None:
            statement = statement.where(AuditEvent.event_type == event_type)
        if resource_type is not None:
            statement = statement.where(
                AuditEvent.resource_type == resource_type
            )
        if resource_id is not None:
            statement = statement.where(
                AuditEvent.resource_id == resource_id
            )
        if outcome is not None:
            statement = statement.where(AuditEvent.outcome == outcome)
        if date_from is not None:
            statement = statement.where(AuditEvent.occurred_at >= date_from)
        if date_to is not None:
            statement = statement.where(AuditEvent.occurred_at <= date_to)
        if request_id is not None:
            statement = statement.where(
                AuditEvent.request_id == request_id
            )

        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    AuditEvent.occurred_at < cursor_time,
                    and_(
                        AuditEvent.occurred_at == cursor_time,
                        AuditEvent.id < cursor_id,
                    ),
                )
            )

        events = self.session.scalars(
            statement.order_by(
                AuditEvent.occurred_at.desc(),
                AuditEvent.id.desc(),
            )
            .limit(limit + 1)
        ).all()
        has_more = len(events) > limit
        events = events[:limit]
        items = [
            AuditEventRead(
                id=event.id,
                event_type=event.event_type,
                actor_user_id=event.actor_user_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                outcome=event.outcome,
                details=dict(event.details),
                request_id=event.request_id,
                occurred_at=event.occurred_at,
            )
            for event in events
        ]
        next_cursor = (
            encode_datetime_cursor(events[-1].occurred_at, events[-1].id)
            if has_more and events
            else None
        )
        return Page(items=items, next_cursor=next_cursor)
