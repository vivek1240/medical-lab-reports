"""remove standalone auth tables and user FK

Revision ID: 0002_remove_auth_tables
Revises: 0001_initial_schema
Create Date: 2026-02-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_remove_auth_tables"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sqlite_drop_lab_reports_user_fk() -> None:
    op.execute("PRAGMA foreign_keys=OFF")
    op.execute(
        """
        CREATE TABLE lab_reports_new (
            doc_id VARCHAR(36) NOT NULL PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            patient_name VARCHAR(255) NOT NULL,
            patient_id VARCHAR(50),
            date_of_birth DATE,
            gender VARCHAR(20),
            lab_name VARCHAR(255),
            report_date DATE,
            collection_date DATE,
            sample_type VARCHAR(100),
            physician_name VARCHAR(255),
            original_filename VARCHAR(255),
            raw_parsed_text TEXT,
            created_at DATETIME NOT NULL
        )
        """
    )
    op.execute(
        """
        INSERT INTO lab_reports_new (
            doc_id, user_id, patient_name, patient_id, date_of_birth, gender, lab_name,
            report_date, collection_date, sample_type, physician_name, original_filename,
            raw_parsed_text, created_at
        )
        SELECT
            doc_id, user_id, patient_name, patient_id, date_of_birth, gender, lab_name,
            report_date, collection_date, sample_type, physician_name, original_filename,
            raw_parsed_text, created_at
        FROM lab_reports
        """
    )
    op.drop_table("lab_reports")
    op.rename_table("lab_reports_new", "lab_reports")
    op.create_index("ix_lab_reports_user_id", "lab_reports", ["user_id"], unique=False)
    op.create_index("ix_lab_reports_report_date", "lab_reports", ["report_date"], unique=False)
    op.execute("PRAGMA foreign_keys=ON")


def _sqlite_add_lab_reports_user_fk() -> None:
    op.execute("PRAGMA foreign_keys=OFF")
    op.execute(
        """
        CREATE TABLE lab_reports_old (
            doc_id VARCHAR(36) NOT NULL PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            patient_name VARCHAR(255) NOT NULL,
            patient_id VARCHAR(50),
            date_of_birth DATE,
            gender VARCHAR(20),
            lab_name VARCHAR(255),
            report_date DATE,
            collection_date DATE,
            sample_type VARCHAR(100),
            physician_name VARCHAR(255),
            original_filename VARCHAR(255),
            raw_parsed_text TEXT,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        INSERT INTO lab_reports_old (
            doc_id, user_id, patient_name, patient_id, date_of_birth, gender, lab_name,
            report_date, collection_date, sample_type, physician_name, original_filename,
            raw_parsed_text, created_at
        )
        SELECT
            doc_id, user_id, patient_name, patient_id, date_of_birth, gender, lab_name,
            report_date, collection_date, sample_type, physician_name, original_filename,
            raw_parsed_text, created_at
        FROM lab_reports
        """
    )
    op.drop_table("lab_reports")
    op.rename_table("lab_reports_old", "lab_reports")
    op.create_index("ix_lab_reports_user_id", "lab_reports", ["user_id"], unique=False)
    op.create_index("ix_lab_reports_report_date", "lab_reports", ["report_date"], unique=False)
    op.execute("PRAGMA foreign_keys=ON")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_table("user_sessions")

    if dialect_name == "sqlite":
        _sqlite_drop_lab_reports_user_fk()
    else:
        inspector = sa.inspect(bind)
        fks = inspector.get_foreign_keys("lab_reports")
        fk_name = None
        for fk in fks:
            if fk.get("referred_table") == "users" and "user_id" in (fk.get("constrained_columns") or []):
                fk_name = fk.get("name")
                break
        if fk_name:
            op.drop_constraint(fk_name, "lab_reports", type_="foreignkey")

    op.drop_table("users")


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

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

    if dialect_name == "sqlite":
        _sqlite_add_lab_reports_user_fk()
    else:
        op.create_foreign_key(
            "fk_lab_reports_user_id_users",
            "lab_reports",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

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
