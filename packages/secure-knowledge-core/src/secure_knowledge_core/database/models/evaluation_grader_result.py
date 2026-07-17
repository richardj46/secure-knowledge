from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class EvaluationGraderResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_grader_results"

    evaluation_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evaluation_case_result_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_case_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    grader_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    grader_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1",
    )

    claim_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    claim: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
