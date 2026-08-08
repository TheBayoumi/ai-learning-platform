"""Add history-wide trusted task exposure and unlinkable collision indexes.

Revision ID: 20260808_02
Revises: 20260724_01
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260808_02"
down_revision = "20260724_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_exposures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=160), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", sa.String(length=160), nullable=False),
        sa.Column("item_family_id", sa.String(length=80), nullable=False),
        sa.Column("item_family_version", sa.String(length=40), nullable=False),
        sa.Column("blueprint_id", sa.String(length=80), nullable=False),
        sa.Column("blueprint_version", sa.String(length=40), nullable=False),
        sa.Column("rubric_version", sa.String(length=80), nullable=False),
        sa.Column("plan_version_id", sa.String(length=120), nullable=False),
        sa.Column("semantic_signature", sa.String(length=64), nullable=False),
        sa.Column("semantic_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("semantic_tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("instance_contract_hash", sa.String(length=80), nullable=False),
        sa.Column("high_stakes_eligible", sa.Boolean(), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_task_exposures_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"],
            ["learner_states.learner_id"],
            name="fk_task_exposures_learner_id_learner_states",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_task_exposures"),
        sa.UniqueConstraint("instance_id", name="uq_task_exposures_instance_id"),
        sa.UniqueConstraint(
            "blueprint_id",
            "semantic_signature",
            name="uq_task_exposures_blueprint_semantic",
        ),
    )
    op.create_index("ix_task_exposures_account_id", "task_exposures", ["account_id"])
    op.create_index("ix_task_exposures_learner_id", "task_exposures", ["learner_id"])
    op.create_index("ix_task_exposures_item_family_id", "task_exposures", ["item_family_id"])
    op.create_index("ix_task_exposures_blueprint_id", "task_exposures", ["blueprint_id"])
    op.create_index("ix_task_exposures_served_at", "task_exposures", ["served_at"])

    op.create_table(
        "task_collision_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_family_id", sa.String(length=80), nullable=False),
        sa.Column("blueprint_id", sa.String(length=80), nullable=False),
        sa.Column("semantic_signature", sa.String(length=64), nullable=False),
        sa.Column("semantic_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("semantic_tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_task_collision_fingerprints"),
        sa.UniqueConstraint(
            "blueprint_id",
            "semantic_signature",
            name="uq_task_collision_fingerprints_blueprint_semantic",
        ),
    )
    op.create_index(
        "ix_task_collision_fingerprints_item_family_id",
        "task_collision_fingerprints",
        ["item_family_id"],
    )
    op.create_index(
        "ix_task_collision_fingerprints_blueprint_id",
        "task_collision_fingerprints",
        ["blueprint_id"],
    )
    op.create_index(
        "ix_task_collision_fingerprints_served_at",
        "task_collision_fingerprints",
        ["served_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_collision_fingerprints_served_at",
        table_name="task_collision_fingerprints",
    )
    op.drop_index(
        "ix_task_collision_fingerprints_blueprint_id",
        table_name="task_collision_fingerprints",
    )
    op.drop_index(
        "ix_task_collision_fingerprints_item_family_id",
        table_name="task_collision_fingerprints",
    )
    op.drop_table("task_collision_fingerprints")

    op.drop_index("ix_task_exposures_served_at", table_name="task_exposures")
    op.drop_index("ix_task_exposures_blueprint_id", table_name="task_exposures")
    op.drop_index("ix_task_exposures_item_family_id", table_name="task_exposures")
    op.drop_index("ix_task_exposures_learner_id", table_name="task_exposures")
    op.drop_index("ix_task_exposures_account_id", table_name="task_exposures")
    op.drop_table("task_exposures")
