"""add evaluation human review

Revision ID: c9b4e2a71d56
Revises: a7e1c4f92b63
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "c9b4e2a71d56"
down_revision: str | None = "a7e1c4f92b63"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    review_status = sa.Enum(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "NEEDS_REVISION",
        name="human_review_status",
    )
    review_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "evaluation_case_results",
        sa.Column(
            "human_review_status",
            review_status,
            server_default="PENDING",
            nullable=False,
        ),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("human_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("human_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_evaluation_case_results_reviewed_by_user_id",
        "evaluation_case_results",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_evaluation_case_results_human_review_status"),
        "evaluation_case_results",
        ["human_review_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_case_results_reviewed_by_user_id"),
        "evaluation_case_results",
        ["reviewed_by_user_id"],
        unique=False,
    )
    op.alter_column(
        "evaluation_case_results",
        "human_review_status",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_case_results_reviewed_by_user_id"),
        table_name="evaluation_case_results",
    )
    op.drop_index(
        op.f("ix_evaluation_case_results_human_review_status"),
        table_name="evaluation_case_results",
    )
    op.drop_constraint(
        "fk_evaluation_case_results_reviewed_by_user_id",
        "evaluation_case_results",
        type_="foreignkey",
    )
    op.drop_column("evaluation_case_results", "reviewed_at")
    op.drop_column("evaluation_case_results", "reviewed_by_user_id")
    op.drop_column("evaluation_case_results", "human_notes")
    op.drop_column("evaluation_case_results", "human_score")
    op.drop_column("evaluation_case_results", "human_review_status")
    sa.Enum(name="human_review_status").drop(op.get_bind(), checkfirst=True)
