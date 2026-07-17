"""add document processing attempts

Revision ID: c4f7a2d91e68
Revises: b6e2d9a41c83
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op

revision: str = "c4f7a2d91e68"
down_revision: str | None = "b6e2d9a41c83"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "document_processing_attempts",
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("worker_task_id", sa.String(length=200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_duration_ms", sa.Integer(), nullable=True),
        sa.Column("chunking_duration_ms", sa.Integer(), nullable=True),
        sa.Column("embedding_duration_ms", sa.Integer(), nullable=True),
        sa.Column("total_duration_ms", sa.Integer(), nullable=True),
        sa.Column("extracted_character_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
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
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "attempt_number",
            name="uq_document_processing_attempts_version_number",
        ),
    )
    op.create_index(
        op.f("ix_document_processing_attempts_document_version_id"),
        "document_processing_attempts",
        ["document_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_attempts_worker_task_id"),
        "document_processing_attempts",
        ["worker_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_processing_attempts_worker_task_id"),
        table_name="document_processing_attempts",
    )
    op.drop_index(
        op.f("ix_document_processing_attempts_document_version_id"),
        table_name="document_processing_attempts",
    )
    op.drop_table("document_processing_attempts")
