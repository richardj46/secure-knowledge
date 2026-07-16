"""add evaluation administrator role

Revision ID: e5b7c1d30a82
Revises: d4a6b0c29f71
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "e5b7c1d30a82"
down_revision: str | None = "d4a6b0c29f71"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE organization_role ADD VALUE IF NOT EXISTS "
        "'EVALUATION_ADMIN'"
    )


def downgrade() -> None:
    assigned_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM organization_memberships
            WHERE role = 'EVALUATION_ADMIN'
            """
        )
    ).scalar_one()
    if assigned_count:
        raise RuntimeError(
            "Evaluation administrator memberships must be reassigned before "
            "downgrading."
        )

    op.execute("ALTER TYPE organization_role RENAME TO organization_role_old")
    op.execute(
        "CREATE TYPE organization_role AS ENUM ('OWNER', 'ADMIN', 'MEMBER')"
    )
    op.execute(
        """
        ALTER TABLE organization_memberships
        ALTER COLUMN role TYPE organization_role
        USING role::text::organization_role
        """
    )
    op.execute("DROP TYPE organization_role_old")
