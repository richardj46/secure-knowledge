from datetime import date
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class DailyOrganizationMetric(IdMixin, TimestampMixin, Base):
    __tablename__ = "daily_organization_metrics"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "metric_date",
            name="uq_daily_organization_metrics_organization_date",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    query_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    answer_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    abstention_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    input_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    output_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    estimated_cost_microusd: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    retrieval_latency_sum_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    generation_latency_sum_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    total_latency_sum_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
