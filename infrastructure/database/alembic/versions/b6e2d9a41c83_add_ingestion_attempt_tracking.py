"""add ingestion attempt tracking

Revision ID: b6e2d9a41c83
Revises: a3d8f1c62b95
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b6e2d9a41c83"
down_revision: str | None = "a3d8f1c62b95"
branch_labels: str | None = None
depends_on: str | None = None

DOCUMENT_VERSION_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "QUEUED",
    "EXTRACTING",
    "CHUNKING",
    "EMBEDDING",
    "READY",
    "FAILED",
    name="document_version_status",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column(
            "processing_stage",
            DOCUMENT_VERSION_STATUS_ENUM,
            nullable=True,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "retry_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "last_attempted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE document_versions
        SET
            processing_stage = CASE
                WHEN status = 'FAILED' THEN NULL
                ELSE status
            END,
            attempt_count = CASE
                WHEN processing_started_at IS NULL THEN 0
                ELSE 1
            END,
            last_attempted_at = processing_started_at
        """
    )
    op.alter_column(
        "document_versions",
        "attempt_count",
        server_default=None,
    )
    op.alter_column(
        "document_versions",
        "retry_count",
        server_default=None,
    )
    op.create_index(
        "ix_document_versions_failed_admin_filters",
        "document_versions",
        ["status", "failure_code", "retry_count", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_versions_failed_admin_filters",
        table_name="document_versions",
    )
    op.drop_column("document_versions", "last_attempted_at")
    op.drop_column("document_versions", "retry_count")
    op.drop_column("document_versions", "attempt_count")
    op.drop_column("document_versions", "processing_stage")
