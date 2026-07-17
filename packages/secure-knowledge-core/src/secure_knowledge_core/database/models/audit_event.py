from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from secure_knowledge_core.audit.events import (
    AuditEventType,
    normalize_audit_event_type,
)
from secure_knowledge_core.audit.redaction import (
    redact_audit_details,
    redact_sensitive_text,
)
from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    @validates("event_type")
    def validate_event_type(
        self,
        _key: str,
        value: str | AuditEventType,
    ) -> str:
        return normalize_audit_event_type(value)

    @validates("details")
    def redact_details(
        self,
        _key: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        return redact_audit_details(value)

    @validates("failure_message")
    def redact_failure_message(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        return redact_sensitive_text(value) if value else None
