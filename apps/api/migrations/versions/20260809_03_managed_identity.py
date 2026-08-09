"""Add provider-neutral OIDC identity mappings, roles, and anonymous-account claim audit.

Revision ID: 20260809_03
Revises: 20260808_02
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260809_03"
down_revision = "20260808_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=160), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_account_identities_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_account_identities"),
        sa.UniqueConstraint(
            "issuer",
            "subject",
            name="uq_account_identities_issuer_subject",
        ),
    )
    op.create_index("ix_account_identities_account_id", "account_identities", ["account_id"])

    op.create_table(
        "account_roles",
        sa.Column("account_id", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_account_roles_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("account_id", "role", name="pk_account_roles"),
    )

    op.create_table(
        "identity_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_account_sha256", sa.String(length=64), nullable=False),
        sa.Column("target_account_id", sa.String(length=160), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_account_id"],
            ["accounts.id"],
            name="fk_identity_claims_target_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_claims"),
        sa.UniqueConstraint(
            "source_account_sha256",
            name="uq_identity_claims_source_account_sha256",
        ),
    )
    op.create_index("ix_identity_claims_target_account_id", "identity_claims", ["target_account_id"])


def downgrade() -> None:
    op.drop_index("ix_identity_claims_target_account_id", table_name="identity_claims")
    op.drop_table("identity_claims")
    op.drop_table("account_roles")
    op.drop_index("ix_account_identities_account_id", table_name="account_identities")
    op.drop_table("account_identities")
