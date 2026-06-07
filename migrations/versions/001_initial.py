"""initial tables

Revision ID: 001
Revises:
Create Date: 2026-06-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    op.create_table(
        "tutor_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=False),
        sa.Column("place_of_study", sa.String(length=255), nullable=False),
        sa.Column("price_min", sa.Integer(), nullable=False),
        sa.Column("price_max", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("avatar_file_id", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "student_searches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exam_keyword", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.String(length=512), nullable=False),
        sa.Column("current_level", sa.String(length=255), nullable=False),
        sa.Column("budget_min", sa.Integer(), nullable=True),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("exam_keyword", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.String(length=512), nullable=False),
        sa.Column("current_level", sa.String(length=255), nullable=False),
        sa.Column("budget_text", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="new", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tutor_id"], ["tutor_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("student_searches")
    op.drop_table("tutor_profiles")
    op.drop_table("users")
