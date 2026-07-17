"""add conversations and answer runs

Revision ID: c7d3a5e82f41
Revises: b8c2e4f19a70
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

MESSAGE_ROLE_ENUM = sa.Enum(
    "USER",
    "ASSISTANT",
    "SYSTEM",
    name="message_role",
)
ANSWERABILITY_ENUM = sa.Enum(
    "ANSWERABLE",
    "PARTIALLY_ANSWERABLE",
    "UNANSWERABLE",
    name="answerability",
)
ANSWER_GENERATION_STATUS_ENUM = sa.Enum(
    "PENDING",
    "GENERATING",
    "COMPLETED",
    "FAILED",
    name="answer_generation_status",
)

revision: str = "c7d3a5e82f41"
down_revision: str | None = "b8c2e4f19a70"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversations_organization_id"),
        "conversations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_user_id"),
        "conversations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", MESSAGE_ROLE_ENUM, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
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
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )

    op.create_table(
        "answer_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("retrieval_run_id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("answerability", ANSWERABILITY_ENUM, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column(
            "generation_status",
            ANSWER_GENERATION_STATUS_ENUM,
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
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
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_run_id"],
            ["retrieval_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "conversation_id",
        "organization_id",
        "retrieval_run_id",
        "user_id",
    ):
        op.create_index(
            op.f(f"ix_answer_runs_{column_name}"),
            "answer_runs",
            [column_name],
            unique=False,
        )

    op.create_table(
        "answer_citations",
        sa.Column("answer_run_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["answer_run_id"],
            ["answer_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "answer_run_id",
            "chunk_id",
            name="uq_answer_citations_run_chunk",
        ),
        sa.UniqueConstraint(
            "answer_run_id",
            "citation_index",
            name="uq_answer_citations_run_index",
        ),
    )
    for column_name in ("answer_run_id", "chunk_id", "document_id"):
        op.create_index(
            op.f(f"ix_answer_citations_{column_name}"),
            "answer_citations",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in ("document_id", "chunk_id", "answer_run_id"):
        op.drop_index(
            op.f(f"ix_answer_citations_{column_name}"),
            table_name="answer_citations",
        )
    op.drop_table("answer_citations")

    for column_name in (
        "user_id",
        "retrieval_run_id",
        "organization_id",
        "conversation_id",
    ):
        op.drop_index(
            op.f(f"ix_answer_runs_{column_name}"),
            table_name="answer_runs",
        )
    op.drop_table("answer_runs")

    op.drop_index(
        op.f("ix_messages_conversation_id"),
        table_name="messages",
    )
    op.drop_table("messages")

    op.drop_index(
        op.f("ix_conversations_user_id"),
        table_name="conversations",
    )
    op.drop_index(
        op.f("ix_conversations_organization_id"),
        table_name="conversations",
    )
    op.drop_table("conversations")

    ANSWER_GENERATION_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
    ANSWERABILITY_ENUM.drop(op.get_bind(), checkfirst=True)
    MESSAGE_ROLE_ENUM.drop(op.get_bind(), checkfirst=True)
