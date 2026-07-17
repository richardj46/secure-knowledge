"""expand answer run provider metadata

Revision ID: a6e4c8f21d35
Revises: f2a9c4d71b83
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "a6e4c8f21d35"
down_revision: str | None = "f2a9c4d71b83"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "answer_runs",
        sa.Column("provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "answer_runs",
        sa.Column("provider_request_id", sa.String(length=200), nullable=True),
    )
    op.create_index(
        op.f("ix_answer_runs_provider_request_id"),
        "answer_runs",
        ["provider_request_id"],
        unique=False,
    )

    op.alter_column(
        "answer_runs",
        "prompt_tokens",
        new_column_name="input_tokens",
    )
    op.alter_column(
        "answer_runs",
        "completion_tokens",
        new_column_name="output_tokens",
    )
    op.add_column(
        "answer_runs",
        sa.Column("total_tokens", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE answer_runs
        SET total_tokens = COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)
        WHERE input_tokens IS NOT NULL OR output_tokens IS NOT NULL
        """
    )

    op.add_column(
        "answer_runs",
        sa.Column("estimated_cost_microusd", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE answer_runs
        SET estimated_cost_microusd =
            CAST(ROUND(estimated_cost * 1000000) AS INTEGER)
        WHERE estimated_cost IS NOT NULL
        """
    )
    op.drop_column("answer_runs", "estimated_cost")

    op.alter_column(
        "answer_runs",
        "latency_ms",
        new_column_name="generation_duration_ms",
    )
    op.alter_column(
        "answer_runs",
        "generation_status",
        new_column_name="status",
    )
    op.alter_column(
        "answer_runs",
        "error_code",
        new_column_name="failure_code",
    )


def downgrade() -> None:
    op.alter_column(
        "answer_runs",
        "failure_code",
        new_column_name="error_code",
    )
    op.alter_column(
        "answer_runs",
        "status",
        new_column_name="generation_status",
    )
    op.alter_column(
        "answer_runs",
        "generation_duration_ms",
        new_column_name="latency_ms",
    )

    op.add_column(
        "answer_runs",
        sa.Column(
            "estimated_cost",
            sa.Numeric(precision=14, scale=8),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE answer_runs
        SET estimated_cost = estimated_cost_microusd / 1000000.0
        WHERE estimated_cost_microusd IS NOT NULL
        """
    )
    op.drop_column("answer_runs", "estimated_cost_microusd")

    op.drop_column("answer_runs", "total_tokens")
    op.alter_column(
        "answer_runs",
        "output_tokens",
        new_column_name="completion_tokens",
    )
    op.alter_column(
        "answer_runs",
        "input_tokens",
        new_column_name="prompt_tokens",
    )

    op.drop_index(
        op.f("ix_answer_runs_provider_request_id"),
        table_name="answer_runs",
    )
    op.drop_column("answer_runs", "provider_request_id")
    op.drop_column("answer_runs", "provider")
