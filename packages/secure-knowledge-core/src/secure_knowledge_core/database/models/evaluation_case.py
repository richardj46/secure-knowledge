from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class EvaluationCase(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_cases"

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "external_id",
            name="uq_evaluation_cases_dataset_external_id",
        ),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    definition: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
    )

    tags: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )
