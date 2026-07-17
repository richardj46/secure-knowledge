"""expand retrieval traces for administrative inspection

Revision ID: e2c7a9f41b65
Revises: d8f2a6c91e47
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e2c7a9f41b65"
down_revision: str | None = "d8f2a6c91e47"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "workspace_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "fused_result_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "selected_result_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "retrieval_configuration_version",
            sa.String(length=100),
            server_default="hybrid-rrf-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "authorization_policy_version",
            sa.String(length=100),
            server_default="document-access-v1",
            nullable=False,
        ),
    )
    for column_name in (
        "embedding_duration_ms",
        "vector_duration_ms",
        "keyword_duration_ms",
        "fusion_duration_ms",
    ):
        op.add_column(
            "retrieval_runs",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )

    op.execute(
        """
        UPDATE retrieval_runs
        SET fused_result_count = final_result_count
        """
    )
    op.alter_column(
        "retrieval_runs",
        "workspace_ids",
        server_default=None,
    )
    op.alter_column(
        "retrieval_runs",
        "fused_result_count",
        server_default=None,
    )
    op.alter_column(
        "retrieval_runs",
        "selected_result_count",
        server_default=None,
    )
    op.alter_column(
        "retrieval_runs",
        "retrieval_configuration_version",
        server_default=None,
    )
    op.alter_column(
        "retrieval_runs",
        "authorization_policy_version",
        server_default=None,
    )
    op.create_index(
        "ix_retrieval_runs_organization_created_at",
        "retrieval_runs",
        ["organization_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "retrieval_results",
        sa.Column(
            "selected_for_context",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_results",
        sa.Column("permission_path", sa.String(length=50), nullable=True),
    )
    op.alter_column(
        "retrieval_results",
        "selected_for_context",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("retrieval_results", "permission_path")
    op.drop_column("retrieval_results", "selected_for_context")

    op.drop_index(
        "ix_retrieval_runs_organization_created_at",
        table_name="retrieval_runs",
    )
    for column_name in (
        "fusion_duration_ms",
        "keyword_duration_ms",
        "vector_duration_ms",
        "embedding_duration_ms",
        "authorization_policy_version",
        "retrieval_configuration_version",
        "selected_result_count",
        "fused_result_count",
        "workspace_ids",
    ):
        op.drop_column("retrieval_runs", column_name)
