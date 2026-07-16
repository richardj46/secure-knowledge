"""refine evaluation case results

Revision ID: e7b1f5c94a26
Revises: d6a9e4b83f15
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7b1f5c94a26"
down_revision: str | None = "d6a9e4b83f15"
branch_labels: str | None = None
depends_on: str | None = None

EVALUATION_CASE_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "PASSED",
    "FAILED",
    "ERROR",
    name="evaluation_case_status",
    create_type=False,
)


def upgrade() -> None:
    for column in ("answer_run_id", "retrieval_run_id", "status"):
        op.drop_index(
            op.f(f"ix_evaluation_case_results_{column}"),
            table_name="evaluation_case_results",
        )

    op.drop_constraint(
        "evaluation_case_results_answer_run_id_fkey",
        "evaluation_case_results",
        type_="foreignkey",
    )
    op.drop_constraint(
        "evaluation_case_results_retrieval_run_id_fkey",
        "evaluation_case_results",
        type_="foreignkey",
    )

    EVALUATION_CASE_STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE evaluation_case_results
        ALTER COLUMN status TYPE evaluation_case_status
        USING upper(status)::evaluation_case_status
        """
    )

    op.alter_column(
        "evaluation_case_results",
        "duration_ms",
        new_column_name="latency_ms",
    )
    op.alter_column(
        "evaluation_case_results",
        "failure_code",
        new_column_name="error_code",
    )
    op.alter_column(
        "evaluation_case_results",
        "failure_message",
        new_column_name="error_message",
    )

    op.add_column(
        "evaluation_case_results",
        sa.Column("actual_answerability", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("actual_answer", sa.Text(), nullable=True),
    )
    for column in (
        "retrieved_document_ids",
        "retrieved_chunk_ids",
        "context_chunk_ids",
    ):
        op.add_column(
            "evaluation_case_results",
            sa.Column(
                column,
                postgresql.JSONB(),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
        op.alter_column(
            "evaluation_case_results",
            column,
            server_default=None,
        )

    op.add_column(
        "evaluation_case_results",
        sa.Column("estimated_cost_microusd", sa.Integer(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("deterministic_passed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "evaluation_case_results",
        sa.Column("overall_score", sa.Float(), nullable=True),
    )
    op.drop_column("evaluation_case_results", "output_data")


def downgrade() -> None:
    op.add_column(
        "evaluation_case_results",
        sa.Column("output_data", sa.JSON(), nullable=True),
    )
    op.drop_column("evaluation_case_results", "overall_score")
    op.drop_column("evaluation_case_results", "deterministic_passed")
    op.drop_column("evaluation_case_results", "estimated_cost_microusd")
    op.drop_column("evaluation_case_results", "context_chunk_ids")
    op.drop_column("evaluation_case_results", "retrieved_chunk_ids")
    op.drop_column("evaluation_case_results", "retrieved_document_ids")
    op.drop_column("evaluation_case_results", "actual_answer")
    op.drop_column("evaluation_case_results", "actual_answerability")

    op.alter_column(
        "evaluation_case_results",
        "error_message",
        new_column_name="failure_message",
    )
    op.alter_column(
        "evaluation_case_results",
        "error_code",
        new_column_name="failure_code",
    )
    op.alter_column(
        "evaluation_case_results",
        "latency_ms",
        new_column_name="duration_ms",
    )

    op.execute(
        """
        ALTER TABLE evaluation_case_results
        ALTER COLUMN status TYPE varchar(50)
        USING lower(status::text)
        """
    )
    EVALUATION_CASE_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)

    op.create_foreign_key(
        "evaluation_case_results_retrieval_run_id_fkey",
        "evaluation_case_results",
        "retrieval_runs",
        ["retrieval_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "evaluation_case_results_answer_run_id_fkey",
        "evaluation_case_results",
        "answer_runs",
        ["answer_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    for column in ("answer_run_id", "retrieval_run_id", "status"):
        op.create_index(
            op.f(f"ix_evaluation_case_results_{column}"),
            "evaluation_case_results",
            [column],
            unique=False,
        )
