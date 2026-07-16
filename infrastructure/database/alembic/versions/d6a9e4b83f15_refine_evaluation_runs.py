"""refine evaluation runs

Revision ID: d6a9e4b83f15
Revises: c5f8d3a72e94
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6a9e4b83f15"
down_revision: str | None = "c5f8d3a72e94"
branch_labels: str | None = None
depends_on: str | None = None

EVALUATION_RUN_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    name="evaluation_run_status",
    create_type=False,
)


def upgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_runs_evaluation_dataset_id"),
        table_name="evaluation_runs",
    )
    op.drop_index(
        op.f("ix_evaluation_runs_status"),
        table_name="evaluation_runs",
    )
    op.drop_index(
        op.f("ix_evaluation_runs_user_id"),
        table_name="evaluation_runs",
    )

    op.alter_column(
        "evaluation_runs",
        "evaluation_dataset_id",
        new_column_name="dataset_id",
    )
    op.alter_column(
        "evaluation_runs",
        "user_id",
        new_column_name="started_by_user_id",
    )
    op.alter_column(
        "evaluation_runs",
        "total_case_count",
        new_column_name="total_cases",
    )
    op.alter_column(
        "evaluation_runs",
        "completed_case_count",
        new_column_name="completed_cases",
    )

    EVALUATION_RUN_STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE evaluation_runs
        ALTER COLUMN status TYPE evaluation_run_status
        USING upper(status)::evaluation_run_status
        """
    )
    op.execute(
        """
        ALTER TABLE evaluation_runs
        ALTER COLUMN configuration TYPE jsonb
        USING configuration::jsonb
        """
    )

    op.add_column(
        "evaluation_runs",
        sa.Column("code_revision", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column(
            "passed_cases",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column(
            "failed_cases",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("failure_message", sa.Text(), nullable=True),
    )
    op.alter_column("evaluation_runs", "passed_cases", server_default=None)
    op.alter_column("evaluation_runs", "failed_cases", server_default=None)

    op.create_index(
        op.f("ix_evaluation_runs_dataset_id"),
        "evaluation_runs",
        ["dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_runs_dataset_id"),
        table_name="evaluation_runs",
    )
    op.drop_column("evaluation_runs", "failure_message")
    op.drop_column("evaluation_runs", "failed_cases")
    op.drop_column("evaluation_runs", "passed_cases")
    op.drop_column("evaluation_runs", "code_revision")

    op.execute(
        """
        ALTER TABLE evaluation_runs
        ALTER COLUMN configuration TYPE json
        USING configuration::json
        """
    )
    op.execute(
        """
        ALTER TABLE evaluation_runs
        ALTER COLUMN status TYPE varchar(50)
        USING lower(status::text)
        """
    )
    EVALUATION_RUN_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)

    op.alter_column(
        "evaluation_runs",
        "completed_cases",
        new_column_name="completed_case_count",
    )
    op.alter_column(
        "evaluation_runs",
        "total_cases",
        new_column_name="total_case_count",
    )
    op.alter_column(
        "evaluation_runs",
        "started_by_user_id",
        new_column_name="user_id",
    )
    op.alter_column(
        "evaluation_runs",
        "dataset_id",
        new_column_name="evaluation_dataset_id",
    )

    for column in ("evaluation_dataset_id", "status", "user_id"):
        op.create_index(
            op.f(f"ix_evaluation_runs_{column}"),
            "evaluation_runs",
            [column],
            unique=False,
        )
