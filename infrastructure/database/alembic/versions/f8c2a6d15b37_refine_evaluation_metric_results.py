"""refine evaluation metric results

Revision ID: f8c2a6d15b37
Revises: e7b1f5c94a26
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "f8c2a6d15b37"
down_revision: str | None = "e7b1f5c94a26"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_evaluation_metric_results_case_metric",
        "evaluation_metric_results",
        type_="unique",
    )
    op.alter_column(
        "evaluation_metric_results",
        "evaluation_case_result_id",
        nullable=True,
    )
    op.execute(
        """
        ALTER TABLE evaluation_metric_results
        ALTER COLUMN details TYPE jsonb
        USING details::jsonb
        """
    )
    op.add_column(
        "evaluation_metric_results",
        sa.Column(
            "metric_version",
            sa.String(length=50),
            server_default="v1",
            nullable=False,
        ),
    )
    op.alter_column(
        "evaluation_metric_results",
        "metric_version",
        server_default=None,
    )
    op.add_column(
        "evaluation_metric_results",
        sa.Column("threshold", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    aggregate_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM evaluation_metric_results
            WHERE evaluation_case_result_id IS NULL
            """
        )
    ).scalar_one()

    if aggregate_count:
        raise RuntimeError(
            "Run-level metric results must be removed before downgrading."
        )

    op.drop_column("evaluation_metric_results", "threshold")
    op.drop_column("evaluation_metric_results", "metric_version")
    op.execute(
        """
        ALTER TABLE evaluation_metric_results
        ALTER COLUMN details TYPE json
        USING details::json
        """
    )
    op.alter_column(
        "evaluation_metric_results",
        "evaluation_case_result_id",
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_evaluation_metric_results_case_metric",
        "evaluation_metric_results",
        ["evaluation_case_result_id", "metric_name"],
    )
