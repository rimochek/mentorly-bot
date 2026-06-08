"""tutor stats and tutor_contacts

Revision ID: 002
Revises: 001
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tutor_profiles",
        sa.Column("views_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("contacts_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("last_shown_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("shown_today_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("last_stats_reset_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tutor_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("student_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tutor_id"], ["tutor_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tutor_id", "student_telegram_id", name="uq_tutor_contacts_tutor_student"),
    )


def downgrade() -> None:
    op.drop_table("tutor_contacts")
    op.drop_column("tutor_profiles", "last_stats_reset_at")
    op.drop_column("tutor_profiles", "shown_today_count")
    op.drop_column("tutor_profiles", "last_shown_at")
    op.drop_column("tutor_profiles", "contacts_count")
    op.drop_column("tutor_profiles", "views_count")
