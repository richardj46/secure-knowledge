"""refine evaluation cases

Revision ID: c5f8d3a72e94
Revises: b4e7a2c91d63
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5f8d3a72e94"
down_revision: str | None = "b4e7a2c91d63"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_cases_category"),
        table_name="evaluation_cases",
    )
    op.drop_index(
        op.f("ix_evaluation_cases_evaluation_dataset_id"),
        table_name="evaluation_cases",
    )
    op.drop_constraint(
        "uq_evaluation_cases_dataset_key",
        "evaluation_cases",
        type_="unique",
    )

    op.alter_column(
        "evaluation_cases",
        "evaluation_dataset_id",
        new_column_name="dataset_id",
    )
    op.alter_column(
        "evaluation_cases",
        "case_key",
        new_column_name="external_id",
    )

    op.add_column(
        "evaluation_cases",
        sa.Column("name", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("question", sa.Text(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("definition", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column(
            "tags",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE evaluation_cases AS evaluation_case
        SET
            name = evaluation_case.external_id,
            user_id = NULLIF(evaluation_case.input_data ->> 'user_id', '')::uuid,
            organization_id = evaluation_dataset.organization_id,
            question = COALESCE(
                evaluation_case.input_data ->> 'question',
                evaluation_case.external_id
            ),
            definition = jsonb_build_object(
                'category', evaluation_case.category,
                'description', evaluation_case.description,
                'input', evaluation_case.input_data,
                'expected', evaluation_case.expected_data
            )
        FROM evaluation_datasets AS evaluation_dataset
        WHERE evaluation_dataset.id = evaluation_case.dataset_id
        """
    )

    missing_user_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM evaluation_cases
            WHERE user_id IS NULL
            """
        )
    ).scalar_one()

    if missing_user_count:
        raise RuntimeError(
            "Existing evaluation cases must include input_data.user_id before "
            "this migration can continue."
        )

    for column in ("definition", "name", "organization_id", "question", "user_id"):
        op.alter_column("evaluation_cases", column, nullable=False)

    op.create_foreign_key(
        "fk_evaluation_cases_organization_id_organizations",
        "evaluation_cases",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evaluation_cases_user_id_users",
        "evaluation_cases",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_evaluation_cases_dataset_id"),
        "evaluation_cases",
        ["dataset_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_evaluation_cases_dataset_external_id",
        "evaluation_cases",
        ["dataset_id", "external_id"],
    )

    op.drop_column("evaluation_cases", "expected_data")
    op.drop_column("evaluation_cases", "input_data")
    op.drop_column("evaluation_cases", "description")
    op.drop_column("evaluation_cases", "category")
    op.alter_column("evaluation_cases", "tags", server_default=None)


def downgrade() -> None:
    op.add_column(
        "evaluation_cases",
        sa.Column("category", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("input_data", sa.JSON(), nullable=True),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("expected_data", sa.JSON(), nullable=True),
    )
    op.execute(
        """
        UPDATE evaluation_cases
        SET
            category = COALESCE(definition ->> 'category', 'unspecified'),
            description = definition ->> 'description',
            input_data = COALESCE(definition -> 'input', '{}'::jsonb),
            expected_data = COALESCE(definition -> 'expected', '{}'::jsonb)
        """
    )
    for column in ("category", "expected_data", "input_data"):
        op.alter_column("evaluation_cases", column, nullable=False)

    op.drop_constraint(
        "uq_evaluation_cases_dataset_external_id",
        "evaluation_cases",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_evaluation_cases_dataset_id"),
        table_name="evaluation_cases",
    )
    op.drop_constraint(
        "fk_evaluation_cases_user_id_users",
        "evaluation_cases",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_evaluation_cases_organization_id_organizations",
        "evaluation_cases",
        type_="foreignkey",
    )

    op.drop_column("evaluation_cases", "tags")
    op.drop_column("evaluation_cases", "definition")
    op.drop_column("evaluation_cases", "question")
    op.drop_column("evaluation_cases", "organization_id")
    op.drop_column("evaluation_cases", "user_id")
    op.drop_column("evaluation_cases", "name")

    op.alter_column(
        "evaluation_cases",
        "external_id",
        new_column_name="case_key",
    )
    op.alter_column(
        "evaluation_cases",
        "dataset_id",
        new_column_name="evaluation_dataset_id",
    )
    op.create_unique_constraint(
        "uq_evaluation_cases_dataset_key",
        "evaluation_cases",
        ["evaluation_dataset_id", "case_key"],
    )
    op.create_index(
        op.f("ix_evaluation_cases_evaluation_dataset_id"),
        "evaluation_cases",
        ["evaluation_dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_category"),
        "evaluation_cases",
        ["category"],
        unique=False,
    )
