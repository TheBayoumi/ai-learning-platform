"""SQLAlchemy Core tables for provider-neutral account identity mappings."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from ai_learning_platform_api.persistence.models import metadata

account_identities = Table(
    "account_identities",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("issuer", String(512), nullable=False),
    Column("subject", String(255), nullable=False),
    Column("email", String(320), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("issuer", "subject", name="uq_account_identities_issuer_subject"),
)

account_roles = Table(
    "account_roles",
    metadata,
    Column(
        "account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("role", String(32), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

identity_claims = Table(
    "identity_claims",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("source_account_sha256", String(64), nullable=False, unique=True),
    Column(
        "target_account_id",
        String(160),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("claimed_at", DateTime(timezone=True), nullable=False),
)
