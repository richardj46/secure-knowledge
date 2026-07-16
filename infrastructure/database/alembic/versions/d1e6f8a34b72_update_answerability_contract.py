"""update answerability contract

Revision ID: d1e6f8a34b72
Revises: c7d3a5e82f41
Create Date: 2026-07-16

"""
from alembic import op

revision: str = "d1e6f8a34b72"
down_revision: str | None = "c7d3a5e82f41"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE answerability RENAME TO answerability_previous")
    op.execute(
        "CREATE TYPE answerability AS ENUM "
        "('ANSWERABLE', 'PARTIALLY_ANSWERABLE', 'NOT_FOUND', 'AMBIGUOUS')"
    )
    op.execute(
        """
        ALTER TABLE answer_runs
        ALTER COLUMN answerability TYPE answerability
        USING (
            CASE answerability::text
                WHEN 'UNANSWERABLE' THEN 'NOT_FOUND'
                ELSE answerability::text
            END
        )::answerability
        """
    )
    op.execute("DROP TYPE answerability_previous")


def downgrade() -> None:
    op.execute("ALTER TYPE answerability RENAME TO answerability_expanded")
    op.execute(
        "CREATE TYPE answerability AS ENUM "
        "('ANSWERABLE', 'PARTIALLY_ANSWERABLE', 'UNANSWERABLE')"
    )
    op.execute(
        """
        ALTER TABLE answer_runs
        ALTER COLUMN answerability TYPE answerability
        USING (
            CASE answerability::text
                WHEN 'NOT_FOUND' THEN 'UNANSWERABLE'
                WHEN 'AMBIGUOUS' THEN 'UNANSWERABLE'
                ELSE answerability::text
            END
        )::answerability
        """
    )
    op.execute("DROP TYPE answerability_expanded")
