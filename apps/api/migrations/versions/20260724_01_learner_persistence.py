"""Create durable learner state, event ledger, and transactional outbox.

Revision ID: 20260724_01
Revises:
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260724_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial provider-neutral persistence schema."""
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_table(
        "learner_states",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_learner_states_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("learner_id", name="pk_learner_states"),
        sa.UniqueConstraint(
            "account_id",
            "learner_id",
            name="uq_learner_states_account_learner",
        ),
    )
    op.create_index(
        "ix_learner_states_account_id",
        "learner_states",
        ["account_id"],
        unique=False,
    )
    op.create_table(
        "learner_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=160), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("command_hash", sa.String(length=64), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_learner_events_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"],
            ["learner_states.learner_id"],
            name="fk_learner_events_learner_id_learner_states",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_learner_events"),
        sa.UniqueConstraint(
            "account_id",
            "idempotency_key",
            name="uq_learner_events_account_idempotency",
        ),
        sa.UniqueConstraint(
            "learner_id",
            "aggregate_version",
            name="uq_learner_events_learner_version",
        ),
    )
    op.create_index(
        "ix_learner_events_account_id",
        "learner_events",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_learner_events_learner_id",
        "learner_events",
        ["learner_id"],
        unique=False,
    )
    op.create_table(
        "outbox_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["learner_events.id"],
            name="fk_outbox_records_event_id_learner_events",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_records"),
        sa.UniqueConstraint("event_id", name="uq_outbox_records_event_id"),
    )


def downgrade() -> None:
    """Remove the persistence schema in reverse dependency order."""
    op.drop_table("outbox_records")
    op.drop_index("ix_learner_events_learner_id", table_name="learner_events")
    op.drop_index("ix_learner_events_account_id", table_name="learner_events")
    op.drop_table("learner_events")
    op.drop_index("ix_learner_states_account_id", table_name="learner_states")
    op.drop_table("learner_states")
    op.drop_table("accounts")
