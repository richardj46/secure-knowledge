"""add evaluation conversations

Revision ID: b2e4f8a07d59
Revises: a1d3e7f96c48
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "b2e4f8a07d59"
down_revision: str | None = "a1d3e7f96c48"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "is_evaluation",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.alter_column("conversations", "is_evaluation", server_default=None)
    op.add_column(
        "conversations",
        sa.Column("evaluation_case_result_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_evaluation_case_result_id",
        "conversations",
        "evaluation_case_results",
        ["evaluation_case_result_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_conversations_evaluation_case_result_id",
        "conversations",
        ["evaluation_case_result_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_conversations_evaluation_case_result_id",
        "conversations",
        type_="unique",
    )
    op.drop_constraint(
        "fk_conversations_evaluation_case_result_id",
        "conversations",
        type_="foreignkey",
    )
    op.drop_column("conversations", "evaluation_case_result_id")
    op.drop_column("conversations", "is_evaluation")
