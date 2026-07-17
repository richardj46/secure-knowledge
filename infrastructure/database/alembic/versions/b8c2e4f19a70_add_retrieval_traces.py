"""add retrieval traces

Revision ID: b8c2e4f19a70
Revises: e91c7b4d2a60
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "b8c2e4f19a70"
down_revision: str | None = "e91c7b4d2a60"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column("vector_candidate_count", sa.Integer(), nullable=False),
        sa.Column("keyword_candidate_count", sa.Integer(), nullable=False),
        sa.Column("final_result_count", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
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
        op.f("ix_retrieval_runs_organization_id"),
        "retrieval_runs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieval_runs_query_hash"),
        "retrieval_runs",
        ["query_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieval_runs_user_id"),
        "retrieval_runs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "retrieval_results",
        sa.Column("retrieval_run_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("final_rank", sa.Integer(), nullable=False),
        sa.Column("fused_score", sa.Float(), nullable=False),
        sa.Column("vector_rank", sa.Integer(), nullable=True),
        sa.Column("keyword_rank", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["retrieval_run_id"],
            ["retrieval_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retrieval_run_id",
            "chunk_id",
            name="uq_retrieval_results_run_chunk",
        ),
        sa.UniqueConstraint(
            "retrieval_run_id",
            "final_rank",
            name="uq_retrieval_results_run_rank",
        ),
    )
    op.create_index(
        op.f("ix_retrieval_results_chunk_id"),
        "retrieval_results",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieval_results_document_id"),
        "retrieval_results",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieval_results_retrieval_run_id"),
        "retrieval_results",
        ["retrieval_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_retrieval_results_retrieval_run_id"),
        table_name="retrieval_results",
    )
    op.drop_index(
        op.f("ix_retrieval_results_document_id"),
        table_name="retrieval_results",
    )
    op.drop_index(
        op.f("ix_retrieval_results_chunk_id"),
        table_name="retrieval_results",
    )
    op.drop_table("retrieval_results")

    op.drop_index(
        op.f("ix_retrieval_runs_user_id"),
        table_name="retrieval_runs",
    )
    op.drop_index(
        op.f("ix_retrieval_runs_query_hash"),
        table_name="retrieval_runs",
    )
    op.drop_index(
        op.f("ix_retrieval_runs_organization_id"),
        table_name="retrieval_runs",
    )
    op.drop_table("retrieval_runs")
