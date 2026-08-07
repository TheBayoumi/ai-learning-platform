"""Verify that a migrated PostgreSQL database is safe to activate or restore.

The optional write check executes inside one transaction that is always rolled back. The
script never prints the database URL, host, role, password, or generated record identifiers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from ai_learning_platform_api.persistence.database import DatabaseRuntime

_REQUIRED_TABLES = frozenset(
    {
        "accounts",
        "alembic_version",
        "learner_events",
        "learner_states",
        "outbox_records",
    }
)
_REQUIRED_CASCADES = {
    "fk_learner_events_account_id_accounts": "CASCADE",
    "fk_learner_events_learner_id_learner_states": "CASCADE",
    "fk_learner_states_account_id_accounts": "CASCADE",
    "fk_outbox_records_event_id_learner_events": "CASCADE",
}


class RecoveryVerificationError(RuntimeError):
    """A deterministic recovery-posture contract failure."""


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """Sanitized recovery verification output."""

    revision: str
    table_count: int
    cascade_count: int
    write_check: bool

    def as_json(self) -> str:
        return json.dumps(
            {
                "cascade_count": self.cascade_count,
                "revision": self.revision,
                "status": "passed",
                "table_count": self.table_count,
                "write_check": self.write_check,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


async def verify_recovery(
    *,
    database_url: str,
    expected_revision: str,
    write_check: bool,
) -> RecoveryReport:
    """Verify schema and optional rollback-only cascade behavior."""
    runtime = DatabaseRuntime.create(database_url)
    try:
        async with runtime.engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != expected_revision:
                raise RecoveryVerificationError("revision_mismatch")

            table_rows = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            tables = {str(row[0]) for row in table_rows}
            missing_tables = _REQUIRED_TABLES - tables
            if missing_tables:
                raise RecoveryVerificationError("required_table_missing")

            cascade_rows = await connection.execute(
                text(
                    "SELECT constraint_name, delete_rule "
                    "FROM information_schema.referential_constraints "
                    "WHERE constraint_schema = 'public'"
                )
            )
            cascades = {str(row[0]): str(row[1]) for row in cascade_rows}
            if any(
                cascades.get(constraint_name) != delete_rule
                for constraint_name, delete_rule in _REQUIRED_CASCADES.items()
            ):
                raise RecoveryVerificationError("cascade_contract_mismatch")

            if write_check:
                await _verify_rollback_only_cascade(connection)

            return RecoveryReport(
                revision=str(revision),
                table_count=len(_REQUIRED_TABLES),
                cascade_count=len(_REQUIRED_CASCADES),
                write_check=write_check,
            )
    finally:
        await runtime.shutdown()


async def _verify_rollback_only_cascade(
    connection: AsyncConnection,
) -> None:
    transaction = await connection.begin_nested()
    account_id = str(uuid4())
    learner_id = uuid4()
    event_id = uuid4()
    outbox_id = uuid4()
    try:
        await connection.execute(
            text(
                "INSERT INTO accounts (id, created_at, updated_at) "
                "VALUES (:account_id, now(), now())"
            ),
            {"account_id": account_id},
        )
        await connection.execute(
            text(
                "INSERT INTO learner_states "
                "(learner_id, account_id, version, state, created_at, updated_at) "
                "VALUES (:learner_id, :account_id, 0, CAST(:state AS JSONB), now(), now())"
            ),
            {"account_id": account_id, "learner_id": learner_id, "state": "{}"},
        )
        await connection.execute(
            text(
                "INSERT INTO learner_events "
                "(id, account_id, learner_id, aggregate_version, event_type, "
                "idempotency_key, command_hash, state, occurred_at) "
                "VALUES (:event_id, :account_id, :learner_id, 0, 'recovery.checked', "
                ":idempotency_key, :command_hash, CAST(:state AS JSONB), now())"
            ),
            {
                "account_id": account_id,
                "command_hash": "0" * 64,
                "event_id": event_id,
                "idempotency_key": f"recovery-{uuid4()}",
                "learner_id": learner_id,
                "state": "{}",
            },
        )
        await connection.execute(
            text(
                "INSERT INTO outbox_records "
                "(id, event_id, topic, payload, created_at, available_at, published_at, "
                "attempts, last_error_code) "
                "VALUES (:outbox_id, :event_id, 'recovery.checked', CAST(:payload AS JSONB), "
                "now(), now(), NULL, 0, NULL)"
            ),
            {"event_id": event_id, "outbox_id": outbox_id, "payload": "{}"},
        )
        await connection.execute(
            text("DELETE FROM accounts WHERE id = :account_id"),
            {"account_id": account_id},
        )

        remaining = 0
        remaining += int(
            await connection.scalar(
                text("SELECT count(*) FROM accounts WHERE id = :account_id"),
                {"account_id": account_id},
            )
            or 0
        )
        remaining += int(
            await connection.scalar(
                text("SELECT count(*) FROM learner_states WHERE learner_id = :learner_id"),
                {"learner_id": learner_id},
            )
            or 0
        )
        remaining += int(
            await connection.scalar(
                text("SELECT count(*) FROM learner_events WHERE id = :event_id"),
                {"event_id": event_id},
            )
            or 0
        )
        remaining += int(
            await connection.scalar(
                text("SELECT count(*) FROM outbox_records WHERE id = :outbox_id"),
                {"outbox_id": outbox_id},
            )
            or 0
        )
        if remaining != 0:
            raise RecoveryVerificationError("rollback_write_check_failed")
    finally:
        await transaction.rollback()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a migrated PostgreSQL recovery candidate without exposing credentials."
    )
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--write-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    database_url = os.environ.get("AI_PLATFORM_DATABASE_URL", "").strip()
    if not database_url:
        print("recovery_verification_failed:database_url_missing", file=sys.stderr)
        return 2
    try:
        report = asyncio.run(
            verify_recovery(
                database_url=database_url,
                expected_revision=args.expected_revision,
                write_check=args.write_check,
            )
        )
    except RecoveryVerificationError as error:
        print(f"recovery_verification_failed:{error}", file=sys.stderr)
        return 1
    except (SQLAlchemyError, ValueError):
        print("recovery_verification_failed:database_operation_failed", file=sys.stderr)
        return 1
    print(report.as_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
