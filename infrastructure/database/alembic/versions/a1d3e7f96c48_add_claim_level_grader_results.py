"""add claim-level grader results

Revision ID: a1d3e7f96c48
Revises: f8c2a6d15b37
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "a1d3e7f96c48"
down_revision: str | None = "f8c2a6d15b37"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_evaluation_grader_results_case_grader",
        "evaluation_grader_results",
        type_="unique",
    )
    op.execute(
        """
        ALTER TABLE evaluation_grader_results
        ALTER COLUMN details TYPE jsonb
        USING details::jsonb
        """
    )
    op.add_column(
        "evaluation_grader_results",
        sa.Column(
            "grader_version",
            sa.String(length=50),
            server_default="v1",
            nullable=False,
        ),
    )
    op.alter_column(
        "evaluation_grader_results",
        "grader_version",
        server_default=None,
    )
    op.add_column(
        "evaluation_grader_results",
        sa.Column("claim_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "evaluation_grader_results",
        sa.Column("claim", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    duplicate_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT evaluation_case_result_id, grader_name
                FROM evaluation_grader_results
                GROUP BY evaluation_case_result_id, grader_name
                HAVING count(*) > 1
            ) AS duplicate_graders
            """
        )
    ).scalar_one()

    if duplicate_count:
        raise RuntimeError(
            "Claim-level grader results must be consolidated before downgrading."
        )

    op.drop_column("evaluation_grader_results", "claim")
    op.drop_column("evaluation_grader_results", "claim_index")
    op.drop_column("evaluation_grader_results", "grader_version")
    op.execute(
        """
        ALTER TABLE evaluation_grader_results
        ALTER COLUMN details TYPE json
        USING details::json
        """
    )
    op.create_unique_constraint(
        "uq_evaluation_grader_results_case_grader",
        "evaluation_grader_results",
        ["evaluation_case_result_id", "grader_name"],
    )
