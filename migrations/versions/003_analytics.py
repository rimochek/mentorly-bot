"""analytics events and user visit tracking

Revision ID: 003
Revises: 002
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("visit_count", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("properties", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index(
        "ix_analytics_events_event_type_created_at",
        "analytics_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_telegram_id_created_at",
        "analytics_events",
        ["telegram_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_events_telegram_id_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_column("users", "visit_count")
    op.drop_column("users", "last_seen_at")
