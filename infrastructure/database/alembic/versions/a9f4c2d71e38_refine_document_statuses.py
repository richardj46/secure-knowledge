"""refine document statuses

Revision ID: a9f4c2d71e38
Revises: 07dc1c9a1c61
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9f4c2d71e38"
down_revision: str | None = "07dc1c9a1c61"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "documents",
        "storage_key",
        existing_type=sa.String(length=1000),
        nullable=True,
    )

    op.execute("ALTER TYPE document_status RENAME TO document_status_previous")
    op.execute(
        "CREATE TYPE document_status AS ENUM "
        "('PENDING', 'STORED', 'QUEUED', 'EXTRACTING', 'CHUNKING', "
        "'EMBEDDING', 'READY', 'FAILED', 'DELETED')"
    )
    op.execute(
        """
        ALTER TABLE documents
        ALTER COLUMN status TYPE document_status
        USING (
            CASE status::text
                WHEN 'PROCESSING' THEN 'EXTRACTING'
                ELSE status::text
            END
        )::document_status
        """
    )
    op.execute("DROP TYPE document_status_previous")

    op.execute(
        "CREATE TYPE document_version_status AS ENUM "
        "('PENDING', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'READY', 'FAILED')"
    )
    op.alter_column(
        "document_versions",
        "extraction_status",
        new_column_name="status",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )
    op.execute(
        """
        ALTER TABLE document_versions
        ALTER COLUMN status TYPE document_version_status
        USING upper(status)::document_version_status
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_versions
        ALTER COLUMN status TYPE VARCHAR(50)
        USING lower(status::text)
        """
    )
    op.alter_column(
        "document_versions",
        "status",
        new_column_name="extraction_status",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )
    op.execute("DROP TYPE document_version_status")

    op.execute("ALTER TYPE document_status RENAME TO document_status_refined")
    op.execute(
        "CREATE TYPE document_status AS ENUM "
        "('PENDING', 'PROCESSING', 'READY', 'FAILED', 'DELETED')"
    )
    op.execute(
        """
        ALTER TABLE documents
        ALTER COLUMN status TYPE document_status
        USING (
            CASE
                WHEN status::text IN (
                    'STORED',
                    'QUEUED',
                    'EXTRACTING',
                    'CHUNKING',
                    'EMBEDDING'
                ) THEN 'PROCESSING'
                ELSE status::text
            END
        )::document_status
        """
    )
    op.execute("DROP TYPE document_status_refined")

    op.alter_column(
        "documents",
        "storage_key",
        existing_type=sa.String(length=1000),
        nullable=False,
    )
