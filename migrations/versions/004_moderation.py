"""tutor moderation and verified mentor

Revision ID: 004
Revises: 003
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tutor_profiles",
        sa.Column("moderation_status", sa.String(length=20), server_default="approved", nullable=False),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tutor_profiles",
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tutor_profiles", "moderated_at")
    op.drop_column("tutor_profiles", "verified_at")
    op.drop_column("tutor_profiles", "is_verified")
    op.drop_column("tutor_profiles", "moderation_status")
