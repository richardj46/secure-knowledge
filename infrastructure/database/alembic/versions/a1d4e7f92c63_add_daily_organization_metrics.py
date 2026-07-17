"""add daily organization metrics

Revision ID: a1d4e7f92c63
Revises: c4f7a2d91e68
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op

revision: str = "a1d4e7f92c63"
down_revision: str | None = "c4f7a2d91e68"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "daily_organization_metrics",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column(
            "query_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "answer_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "abstention_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "input_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "output_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "estimated_cost_microusd",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "retrieval_latency_sum_ms",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "generation_latency_sum_ms",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_latency_sum_ms",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "metric_date",
            name="uq_daily_organization_metrics_organization_date",
        ),
    )
    op.create_index(
        op.f("ix_daily_organization_metrics_metric_date"),
        "daily_organization_metrics",
        ["metric_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_organization_metrics_organization_id"),
        "daily_organization_metrics",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_daily_organization_metrics_organization_id"),
        table_name="daily_organization_metrics",
    )
    op.drop_index(
        op.f("ix_daily_organization_metrics_metric_date"),
        table_name="daily_organization_metrics",
    )
    op.drop_table("daily_organization_metrics")
