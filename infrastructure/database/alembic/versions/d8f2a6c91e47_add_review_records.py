"""add review records

Revision ID: d8f2a6c91e47
Revises: c9b4e2a71d56
Create Date: 2026-07-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8f2a6c91e47"
down_revision: str | None = "c9b4e2a71d56"
branch_labels: str | None = None
depends_on: str | None = None

ANSWER_REVIEW_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "NEEDS_REVISION",
    name="review_status",
    create_type=False,
)

EVALUATION_REVIEW_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "NEEDS_REVISION",
    name="evaluation_review_status",
    create_type=False,
)


def upgrade() -> None:
    ANSWER_REVIEW_STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    EVALUATION_REVIEW_STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "answer_reviews",
        sa.Column("answer_run_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", ANSWER_REVIEW_STATUS_ENUM, nullable=False),
        sa.Column("groundedness_score", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("citation_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "groundedness_score IS NULL "
            "OR groundedness_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_groundedness_score_range",
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR relevance_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_relevance_score_range",
        ),
        sa.CheckConstraint(
            "citation_score IS NULL OR citation_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_citation_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["answer_run_id"],
            ["answer_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("answer_run_id", "reviewer_user_id", "status"):
        op.create_index(
            op.f(f"ix_answer_reviews_{column}"),
            "answer_reviews",
            [column],
            unique=False,
        )

    op.create_table(
        "evaluation_case_reviews",
        sa.Column("evaluation_case_result_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", EVALUATION_REVIEW_STATUS_ENUM, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["reviewer_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "evaluation_case_result_id",
        "reviewer_user_id",
        "status",
    ):
        op.create_index(
            op.f(f"ix_evaluation_case_reviews_{column}"),
            "evaluation_case_reviews",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in reversed(
        (
            "evaluation_case_result_id",
            "reviewer_user_id",
            "status",
        )
    ):
        op.drop_index(
            op.f(f"ix_evaluation_case_reviews_{column}"),
            table_name="evaluation_case_reviews",
        )
    op.drop_table("evaluation_case_reviews")

    for column in reversed(("answer_run_id", "reviewer_user_id", "status")):
        op.drop_index(
            op.f(f"ix_answer_reviews_{column}"),
            table_name="answer_reviews",
        )
    op.drop_table("answer_reviews")

    EVALUATION_REVIEW_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
    ANSWER_REVIEW_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
