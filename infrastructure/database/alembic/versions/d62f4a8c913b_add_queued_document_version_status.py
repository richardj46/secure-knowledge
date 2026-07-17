"""add queued document version status

Revision ID: d62f4a8c913b
Revises: f4a7c1d82b69
Create Date: 2026-07-16

"""
from alembic import op

revision: str = "d62f4a8c913b"
down_revision: str | None = "f4a7c1d82b69"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE document_version_status "
        "ADD VALUE IF NOT EXISTS 'QUEUED' AFTER 'PENDING'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE document_versions SET status = 'PENDING' WHERE status = 'QUEUED'"
    )
    op.execute(
        "ALTER TYPE document_version_status "
        "RENAME TO document_version_status_with_queued"
    )
    op.execute(
        "CREATE TYPE document_version_status AS ENUM "
        "('PENDING', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'READY', 'FAILED')"
    )
    op.execute(
        "ALTER TABLE document_versions ALTER COLUMN status "
        "TYPE document_version_status "
        "USING status::text::document_version_status"
    )
    op.execute("DROP TYPE document_version_status_with_queued")
