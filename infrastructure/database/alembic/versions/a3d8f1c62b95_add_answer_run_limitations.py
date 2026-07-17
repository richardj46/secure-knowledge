"""add answer run limitations

Revision ID: a3d8f1c62b95
Revises: f1a6d3c82e74
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3d8f1c62b95"
down_revision: str | None = "f1a6d3c82e74"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "answer_runs",
        sa.Column(
            "limitations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column(
        "answer_runs",
        "limitations",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("answer_runs", "limitations")
