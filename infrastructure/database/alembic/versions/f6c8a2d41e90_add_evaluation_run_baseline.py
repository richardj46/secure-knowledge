"""add evaluation run baseline

Revision ID: f6c8a2d41e90
Revises: e5b7c1d30a82
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "f6c8a2d41e90"
down_revision: str | None = "e5b7c1d30a82"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column("baseline_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_evaluation_runs_baseline_run_id",
        "evaluation_runs",
        "evaluation_runs",
        ["baseline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_evaluation_runs_baseline_run_id"),
        "evaluation_runs",
        ["baseline_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_runs_baseline_run_id"),
        table_name="evaluation_runs",
    )
    op.drop_constraint(
        "fk_evaluation_runs_baseline_run_id",
        "evaluation_runs",
        type_="foreignkey",
    )
    op.drop_column("evaluation_runs", "baseline_run_id")
