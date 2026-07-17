"""add document chunk search vector

Revision ID: e91c7b4d2a60
Revises: d62f4a8c913b
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e91c7b4d2a60"
down_revision: str | None = "d62f4a8c913b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(content, ''))",
                persisted=True,
            ),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_search_vector",
        table_name="document_chunks",
        postgresql_using="gin",
    )
    op.drop_column("document_chunks", "search_vector")
