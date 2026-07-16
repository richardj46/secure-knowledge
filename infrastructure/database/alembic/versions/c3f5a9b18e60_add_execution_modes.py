"""add execution modes

Revision ID: c3f5a9b18e60
Revises: b2e4f8a07d59
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3f5a9b18e60"
down_revision: str | None = "b2e4f8a07d59"
branch_labels: str | None = None
depends_on: str | None = None

EXECUTION_MODE_ENUM = postgresql.ENUM(
    "PRODUCTION",
    "EVALUATION",
    "TEST",
    name="execution_mode",
    create_type=False,
)

TABLES = ("answer_runs", "conversations", "retrieval_runs")


def upgrade() -> None:
    EXECUTION_MODE_ENUM.create(op.get_bind(), checkfirst=True)

    for table_name in TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "execution_mode",
                EXECUTION_MODE_ENUM,
                server_default="PRODUCTION",
                nullable=False,
            ),
        )

    op.execute(
        """
        UPDATE conversations
        SET execution_mode = 'EVALUATION'
        WHERE is_evaluation = true
        """
    )

    for table_name in TABLES:
        op.alter_column(table_name, "execution_mode", server_default=None)
        op.create_index(
            op.f(f"ix_{table_name}_execution_mode"),
            table_name,
            ["execution_mode"],
            unique=False,
        )


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_index(
            op.f(f"ix_{table_name}_execution_mode"),
            table_name=table_name,
        )
        op.drop_column(table_name, "execution_mode")

    EXECUTION_MODE_ENUM.drop(op.get_bind(), checkfirst=True)
