"""SQLAlchemy Core schema for durable learner state and evidence delivery."""

from __future__ import annotations

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

accounts = Table(
    "accounts",
    metadata,
    String(160),
)

# Define columns after construction so Ruff and SQLAlchemy typing remain explicit.
accounts.append_column(__import__("sqlalchemy").Column("id", String(160), primary_key=True))
accounts.append_column(
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False)
)
accounts.append_column(
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False)
)

learner_states = Table(
    "learner_states",
    metadata,
    __import__("sqlalchemy").Column("learner_id", UUID(as_uuid=True), primary_key=True),
    __import__("sqlalchemy").Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column("version", Integer, nullable=False),
    __import__("sqlalchemy").Column("state", JSONB, nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("account_id", "learner_id", name="uq_learner_states_account_learner"),
)

learner_events = Table(
    "learner_events",
    metadata,
    __import__("sqlalchemy").Column("id", UUID(as_uuid=True), primary_key=True),
    __import__("sqlalchemy").Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column(
        "learner_id",
        UUID(as_uuid=True),
        ForeignKey("learner_states.learner_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column("aggregate_version", Integer, nullable=False),
    __import__("sqlalchemy").Column("event_type", String(120), nullable=False),
    __import__("sqlalchemy").Column("idempotency_key", String(160), nullable=False),
    __import__("sqlalchemy").Column("command_hash", String(64), nullable=False),
    __import__("sqlalchemy").Column("state", JSONB, nullable=False),
    __import__("sqlalchemy").Column("occurred_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "account_id",
        "idempotency_key",
        name="uq_learner_events_account_idempotency",
    ),
    UniqueConstraint(
        "learner_id",
        "aggregate_version",
        name="uq_learner_events_learner_version",
    ),
)

outbox_records = Table(
    "outbox_records",
    metadata,
    __import__("sqlalchemy").Column("id", UUID(as_uuid=True), primary_key=True),
    __import__("sqlalchemy").Column(
        "event_id",
        UUID(as_uuid=True),
        ForeignKey("learner_events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    __import__("sqlalchemy").Column("topic", String(120), nullable=False),
    __import__("sqlalchemy").Column("payload", JSONB, nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False),
    __import__("sqlalchemy").Column("available_at", DateTime(timezone=True), nullable=False),
    __import__("sqlalchemy").Column("published_at", DateTime(timezone=True), nullable=True),
    __import__("sqlalchemy").Column("attempts", Integer, nullable=False, default=0),
    __import__("sqlalchemy").Column("last_error_code", Text, nullable=True),
)
