"""add evaluation tables

Revision ID: b4e7a2c91d63
Revises: a6e4c8f21d35
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "b4e7a2c91d63"
down_revision: str | None = "a6e4c8f21d35"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "name",
            "version",
            name="uq_evaluation_datasets_organization_name_version",
        ),
    )
    op.create_index(
        op.f("ix_evaluation_datasets_organization_id"),
        "evaluation_datasets",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("evaluation_dataset_id", sa.Uuid(), nullable=False),
        sa.Column("case_key", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("expected_data", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_dataset_id"],
            ["evaluation_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_dataset_id",
            "case_key",
            name="uq_evaluation_cases_dataset_key",
        ),
    )
    op.create_index(
        op.f("ix_evaluation_cases_category"),
        "evaluation_cases",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_evaluation_dataset_id"),
        "evaluation_cases",
        ["evaluation_dataset_id"],
        unique=False,
    )

    _create_evaluation_runs()
    _create_evaluation_case_results()
    _create_evaluation_metric_results()
    _create_evaluation_grader_results()


def _create_evaluation_runs() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("evaluation_dataset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("total_case_count", sa.Integer(), nullable=False),
        sa.Column("completed_case_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_dataset_id"],
            ["evaluation_datasets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("evaluation_dataset_id", "organization_id", "status", "user_id"):
        op.create_index(
            op.f(f"ix_evaluation_runs_{column}"),
            "evaluation_runs",
            [column],
            unique=False,
        )


def _create_evaluation_case_results() -> None:
    op.create_table(
        "evaluation_case_results",
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_case_id", sa.Uuid(), nullable=False),
        sa.Column("retrieval_run_id", sa.Uuid(), nullable=True),
        sa.Column("answer_run_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["answer_run_id"], ["answer_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_case_id"], ["evaluation_cases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_run_id"], ["retrieval_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_run_id",
            "evaluation_case_id",
            name="uq_evaluation_case_results_run_case",
        ),
    )
    for column in (
        "answer_run_id",
        "evaluation_case_id",
        "evaluation_run_id",
        "retrieval_run_id",
        "status",
    ):
        op.create_index(
            op.f(f"ix_evaluation_case_results_{column}"),
            "evaluation_case_results",
            [column],
            unique=False,
        )


def _create_evaluation_metric_results() -> None:
    op.create_table(
        "evaluation_metric_results",
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_case_result_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(length=200), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_case_result_id"],
            ["evaluation_case_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_case_result_id",
            "metric_name",
            name="uq_evaluation_metric_results_case_metric",
        ),
    )
    for column in ("evaluation_case_result_id", "evaluation_run_id", "metric_name"):
        op.create_index(
            op.f(f"ix_evaluation_metric_results_{column}"),
            "evaluation_metric_results",
            [column],
            unique=False,
        )


def _create_evaluation_grader_results() -> None:
    op.create_table(
        "evaluation_grader_results",
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_case_result_id", sa.Uuid(), nullable=False),
        sa.Column("grader_name", sa.String(length=200), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_case_result_id"],
            ["evaluation_case_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_case_result_id",
            "grader_name",
            name="uq_evaluation_grader_results_case_grader",
        ),
    )
    for column in ("evaluation_case_result_id", "evaluation_run_id", "grader_name"):
        op.create_index(
            op.f(f"ix_evaluation_grader_results_{column}"),
            "evaluation_grader_results",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("evaluation_grader_results")
    op.drop_table("evaluation_metric_results")
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_datasets")
