"""add evaluation gate decisions

Revision ID: d4a6b0c29f71
Revises: c3f5a9b18e60
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4a6b0c29f71"
down_revision: str | None = "c3f5a9b18e60"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "evaluation_case_results",
        sa.Column("hard_gates_passed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column(
            "hard_gate_violations",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column(
        "evaluation_case_results",
        "hard_gate_violations",
        server_default=None,
    )

    for column in (
        "hard_gates_passed",
        "quality_gates_passed",
        "regression_passed",
    ):
        op.add_column(
            "evaluation_runs",
            sa.Column(column, sa.Boolean(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "regression_passed")
    op.drop_column("evaluation_runs", "quality_gates_passed")
    op.drop_column("evaluation_runs", "hard_gates_passed")
    op.drop_column("evaluation_case_results", "hard_gate_violations")
    op.drop_column("evaluation_case_results", "hard_gates_passed")
