"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "biomarker_reference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("standard_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("common_aliases", sa.Text(), nullable=False),
        sa.Column("typical_unit", sa.String(length=50), nullable=True),
        sa.Column("typical_range_male", sa.String(length=100), nullable=True),
        sa.Column("typical_range_female", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_biomarker_reference_category", "biomarker_reference", ["category"], unique=False)
    op.create_index("ix_biomarker_reference_standard_name", "biomarker_reference", ["standard_name"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "lab_reports",
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("patient_id", sa.String(length=50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("lab_name", sa.String(length=255), nullable=True),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("collection_date", sa.Date(), nullable=True),
        sa.Column("sample_type", sa.String(length=100), nullable=True),
        sa.Column("physician_name", sa.String(length=255), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("raw_parsed_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("doc_id"),
    )
    op.create_index("ix_lab_reports_report_date", "lab_reports", ["report_date"], unique=False)
    op.create_index("ix_lab_reports_user_id", "lab_reports", ["user_id"], unique=False)

    op.create_table(
        "test_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("biomarker_id", sa.Integer(), nullable=True),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=50), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("reference_range", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("flag", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["biomarker_id"], ["biomarker_reference.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["lab_reports.doc_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_results_biomarker_id", "test_results", ["biomarker_id"], unique=False)
    op.create_index("ix_test_results_doc_id", "test_results", ["doc_id"], unique=False)
    op.create_index("ix_test_results_test_name", "test_results", ["test_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_test_results_test_name", table_name="test_results")
    op.drop_index("ix_test_results_doc_id", table_name="test_results")
    op.drop_index("ix_test_results_biomarker_id", table_name="test_results")
    op.drop_table("test_results")

    op.drop_index("ix_lab_reports_user_id", table_name="lab_reports")
    op.drop_index("ix_lab_reports_report_date", table_name="lab_reports")
    op.drop_table("lab_reports")

    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_biomarker_reference_standard_name", table_name="biomarker_reference")
    op.drop_index("ix_biomarker_reference_category", table_name="biomarker_reference")
    op.drop_table("biomarker_reference")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
