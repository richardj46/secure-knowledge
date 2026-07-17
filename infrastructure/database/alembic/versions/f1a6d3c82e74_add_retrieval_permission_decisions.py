"""add retrieval permission decision snapshots

Revision ID: f1a6d3c82e74
Revises: e2c7a9f41b65
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a6d3c82e74"
down_revision: str | None = "e2c7a9f41b65"
branch_labels: str | None = None
depends_on: str | None = None

PERMISSION_PATH_ENUM = postgresql.ENUM(
    "organization_admin",
    "document_owner",
    "organization_visibility",
    "workspace_membership",
    "direct_user_grant",
    "group_grant",
    name="permission_path",
    create_type=False,
)


def upgrade() -> None:
    PERMISSION_PATH_ENUM.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "retrieval_results",
        "permission_path",
        existing_type=sa.String(length=50),
        type_=PERMISSION_PATH_ENUM,
        existing_nullable=True,
        postgresql_using="permission_path::permission_path",
    )
    op.add_column(
        "retrieval_results",
        sa.Column("permission_source_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "retrieval_results",
        sa.Column(
            "authorization_policy_version",
            sa.String(length=100),
            server_default="document-access-v1",
            nullable=False,
        ),
    )
    op.alter_column(
        "retrieval_results",
        "authorization_policy_version",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("retrieval_results", "authorization_policy_version")
    op.drop_column("retrieval_results", "permission_source_id")
    op.alter_column(
        "retrieval_results",
        "permission_path",
        existing_type=PERMISSION_PATH_ENUM,
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using="permission_path::text",
    )
    PERMISSION_PATH_ENUM.drop(op.get_bind(), checkfirst=True)
