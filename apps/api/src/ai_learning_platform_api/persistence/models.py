"""SQLAlchemy Core schema for durable learner state and evidence delivery."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
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
    Column("id", String(160), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

learner_states = Table(
    "learner_states",
    metadata,
    Column("learner_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("version", Integer, nullable=False),
    Column("state", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("account_id", "learner_id", name="uq_learner_states_account_learner"),
)

learner_events = Table(
    "learner_events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column(
        "learner_id",
        UUID(as_uuid=True),
        ForeignKey("learner_states.learner_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("aggregate_version", Integer, nullable=False),
    Column("event_type", String(120), nullable=False),
    Column("idempotency_key", String(160), nullable=False),
    Column("command_hash", String(64), nullable=False),
    Column("state", JSONB, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
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

task_exposures = Table(
    "task_exposures",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column(
        "learner_id",
        UUID(as_uuid=True),
        ForeignKey("learner_states.learner_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("instance_id", String(160), nullable=False, unique=True),
    Column("item_family_id", String(80), nullable=False, index=True),
    Column("item_family_version", String(40), nullable=False),
    Column("blueprint_id", String(80), nullable=False, index=True),
    Column("blueprint_version", String(40), nullable=False),
    Column("rubric_version", String(80), nullable=False),
    Column("plan_version_id", String(120), nullable=False),
    Column("semantic_signature", String(64), nullable=False),
    Column("semantic_fingerprint", String(64), nullable=False),
    Column("semantic_tokens", JSONB, nullable=False),
    Column("high_stakes_eligible", Boolean, nullable=False),
    Column("served_at", DateTime(timezone=True), nullable=False, index=True),
    UniqueConstraint(
        "blueprint_id",
        "semantic_signature",
        name="uq_task_exposures_blueprint_semantic",
    ),
)

outbox_records = Table(
    "outbox_records",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "event_id",
        UUID(as_uuid=True),
        ForeignKey("learner_events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    Column("topic", String(120), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
    Column("attempts", Integer, nullable=False, default=0),
    Column("last_error_code", Text, nullable=True),
)
