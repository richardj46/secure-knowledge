"""link answer messages and citations

Revision ID: f2a9c4d71b83
Revises: d1e6f8a34b72
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "f2a9c4d71b83"
down_revision: str | None = "d1e6f8a34b72"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "answer_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("answer_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_answer_run_id_answer_runs",
        "messages",
        "answer_runs",
        ["answer_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_messages_answer_run_id"),
        "messages",
        ["answer_run_id"],
        unique=False,
    )

    op.add_column(
        "answer_citations",
        sa.Column("message_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "answer_citations",
        sa.Column(
            "claims",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_answer_citations_message_id_messages",
        "answer_citations",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_answer_citations_message_id"),
        "answer_citations",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_answer_citations_message_id"),
        table_name="answer_citations",
    )
    op.drop_constraint(
        "fk_answer_citations_message_id_messages",
        "answer_citations",
        type_="foreignkey",
    )
    op.drop_column("answer_citations", "claims")
    op.drop_column("answer_citations", "message_id")

    op.drop_index(
        op.f("ix_messages_answer_run_id"),
        table_name="messages",
    )
    op.drop_constraint(
        "fk_messages_answer_run_id_answer_runs",
        "messages",
        type_="foreignkey",
    )
    op.drop_column("messages", "answer_run_id")
    op.drop_column("answer_runs", "completed_at")
