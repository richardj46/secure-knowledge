"""add run version snapshots

Revision ID: a7e1c4f92b63
Revises: f6c8a2d41e90
Create Date: 2026-07-16

"""
import sqlalchemy as sa
from alembic import op

revision: str = "a7e1c4f92b63"
down_revision: str | None = "f6c8a2d41e90"
branch_labels: str | None = None
depends_on: str | None = None

VERSION_DEFAULTS = {
    "answer_prompt_version": "answer-v1",
    "grader_prompt_version": "groundedness-v1",
    "chunking_version": "paragraph-token-v1",
    "retrieval_configuration_version": "hybrid-rrf-v1",
    "authorization_policy_version": "document-access-v1",
}


def upgrade() -> None:
    for table_name in ("answer_runs", "evaluation_runs"):
        for column_name, default_value in VERSION_DEFAULTS.items():
            op.add_column(
                table_name,
                sa.Column(
                    column_name,
                    sa.String(length=100),
                    server_default=default_value,
                    nullable=False,
                ),
            )

        op.add_column(
            table_name,
            sa.Column("answer_model", sa.String(length=200), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("embedding_model", sa.String(length=200), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("reranker_model", sa.String(length=200), nullable=True),
        )

    op.execute(
        """
        UPDATE answer_runs
        SET answer_model = model_name
        """
    )
    op.execute(
        """
        UPDATE answer_runs AS answer_run
        SET embedding_model = retrieval_run.embedding_model
        FROM retrieval_runs AS retrieval_run
        WHERE retrieval_run.id = answer_run.retrieval_run_id
        """
    )
    op.execute(
        """
        UPDATE evaluation_runs
        SET
            answer_model = configuration ->> 'answer_model',
            embedding_model = COALESCE(
                configuration ->> 'embedding_model',
                'unversioned'
            ),
            reranker_model = configuration ->> 'reranker_model'
        """
    )
    op.execute(
        """
        UPDATE answer_runs
        SET embedding_model = 'unversioned'
        WHERE embedding_model IS NULL
        """
    )

    op.alter_column("answer_runs", "answer_model", nullable=False)
    op.alter_column("answer_runs", "embedding_model", nullable=False)
    op.alter_column("evaluation_runs", "embedding_model", nullable=False)

    for table_name in ("answer_runs", "evaluation_runs"):
        for column_name in VERSION_DEFAULTS:
            op.alter_column(
                table_name,
                column_name,
                server_default=None,
            )


def downgrade() -> None:
    columns = (
        "authorization_policy_version",
        "retrieval_configuration_version",
        "chunking_version",
        "reranker_model",
        "embedding_model",
        "answer_model",
        "grader_prompt_version",
        "answer_prompt_version",
    )
    for table_name in ("evaluation_runs", "answer_runs"):
        for column_name in columns:
            op.drop_column(table_name, column_name)
