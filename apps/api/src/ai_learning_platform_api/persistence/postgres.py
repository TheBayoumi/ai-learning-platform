"""Transactional PostgreSQL implementation of durable learner-state contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import ValidationError
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from ai_learning_platform_api.learning.schemas import CollisionFingerprintView, LearnerState
from ai_learning_platform_api.persistence.contracts import (
    IdempotencyConflictError,
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateRepository,
    PersistenceUnavailableError,
    ReplayDivergenceError,
    StoredLearnerState,
    TaskExposureConflictError,
    validate_account_id,
)
from ai_learning_platform_api.persistence.models import (
    accounts,
    learner_events,
    learner_states,
    outbox_records,
    task_collision_fingerprints,
    task_exposures,
)

type RowData = Mapping[str, Any] | RowMapping


class PostgresLearnerStateRepository(LearnerStateRepository):
    """Persist snapshots, events, outbox work, and task exposure indexes atomically."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def load(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        """Load only an aggregate owned by the supplied account identifier."""
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(
                        learner_states.c.account_id,
                        learner_states.c.learner_id,
                        learner_states.c.version,
                        learner_states.c.state,
                        learner_states.c.updated_at,
                    ).where(
                        learner_states.c.account_id == account_id,
                        learner_states.c.learner_id == learner_id,
                    )
                )
                row = result.mappings().one_or_none()
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error
        if row is None:
            return None
        return _stored_state(row)

    async def list_task_collision_fingerprints(
        self,
        *,
        item_family_ids: tuple[str, ...],
    ) -> tuple[CollisionFingerprintView, ...]:
        """Return complete unlinkable collision history for the requested item families."""
        if not item_family_ids:
            return ()
        statement = (
            select(
                task_collision_fingerprints.c.item_family_id,
                task_collision_fingerprints.c.blueprint_id,
                task_collision_fingerprints.c.semantic_signature,
                task_collision_fingerprints.c.semantic_fingerprint,
                task_collision_fingerprints.c.semantic_tokens,
                task_collision_fingerprints.c.served_at,
            )
            .where(task_collision_fingerprints.c.item_family_id.in_(item_family_ids))
            .order_by(
                task_collision_fingerprints.c.served_at,
                task_collision_fingerprints.c.id,
            )
        )
        try:
            async with self._engine.connect() as connection:
                rows = (await connection.execute(statement)).mappings().all()
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error
        return tuple(
            CollisionFingerprintView(
                item_family_id=str(row["item_family_id"]),
                blueprint_id=str(row["blueprint_id"]),
                semantic_signature=str(row["semantic_signature"]),
                semantic_fingerprint=str(row["semantic_fingerprint"]),
                semantic_tokens=[str(item) for item in row["semantic_tokens"]],
                served_at=row["served_at"].isoformat(),
            )
            for row in rows
        )

    async def list_account_states(
        self,
        *,
        account_id: str,
    ) -> tuple[StoredLearnerState, ...]:
        """Return all current learner aggregates owned by one account."""
        validate_account_id(account_id)
        statement = (
            select(
                learner_states.c.account_id,
                learner_states.c.learner_id,
                learner_states.c.version,
                learner_states.c.state,
                learner_states.c.updated_at,
            )
            .where(learner_states.c.account_id == account_id)
            .order_by(learner_states.c.learner_id)
        )
        try:
            async with self._engine.connect() as connection:
                rows = (await connection.execute(statement)).mappings().all()
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error
        return tuple(_stored_state(row) for row in rows)

    async def delete_account(self, *, account_id: str) -> bool:
        """Delete personal account history while retaining unlinkable collision tombstones."""
        validate_account_id(account_id)
        try:
            async with self._engine.begin() as connection:
                result = await connection.execute(
                    delete(accounts).where(accounts.c.id == account_id)
                )
                return result.rowcount == 1
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error

    async def replay(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        """Reconstruct one aggregate from its contiguous append-only event sequence."""
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(
                        learner_events.c.account_id,
                        learner_events.c.learner_id,
                        learner_events.c.aggregate_version,
                        learner_events.c.state,
                        learner_events.c.occurred_at,
                    )
                    .where(
                        learner_events.c.account_id == account_id,
                        learner_events.c.learner_id == learner_id,
                    )
                    .order_by(learner_events.c.aggregate_version)
                )
                rows = result.mappings().all()
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error
        if not rows:
            return None
        for expected_version, row in enumerate(rows):
            if int(row["aggregate_version"]) != expected_version:
                raise ReplayDivergenceError
        latest = rows[-1]
        try:
            state = LearnerState.model_validate(latest["state"])
            return StoredLearnerState(
                account_id=str(latest["account_id"]),
                learner_id=latest["learner_id"],
                version=int(latest["aggregate_version"]),
                state=state,
                updated_at=latest["occurred_at"],
            )
        except (ValidationError, ValueError) as error:
            raise ReplayDivergenceError from error

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        """Commit state, event, exposure indexes, and outbox with optimistic concurrency."""
        command_hash = _command_hash(request)
        try:
            async with self._engine.begin() as connection:
                existing = await _find_idempotent(
                    connection,
                    account_id=request.account_id,
                    idempotency_key=request.idempotency_key,
                )
                if existing is not None:
                    return _idempotent_result(existing, command_hash)

                await connection.execute(
                    postgresql_insert(accounts)
                    .values(
                        id=request.account_id,
                        created_at=request.occurred_at,
                        updated_at=request.occurred_at,
                    )
                    .on_conflict_do_update(
                        index_elements=[accounts.c.id],
                        set_={"updated_at": request.occurred_at},
                    )
                )

                next_version = await _write_snapshot(connection, request)
                await _write_task_exposures(connection, request)
                event_id = uuid4()
                state_payload = request.state.model_dump(mode="json")
                await connection.execute(
                    insert(learner_events).values(
                        id=event_id,
                        account_id=request.account_id,
                        learner_id=request.learner_id,
                        aggregate_version=next_version,
                        event_type=request.event_type,
                        idempotency_key=request.idempotency_key,
                        command_hash=command_hash,
                        state=state_payload,
                        occurred_at=request.occurred_at,
                    )
                )
                await connection.execute(
                    insert(outbox_records).values(
                        id=uuid4(),
                        event_id=event_id,
                        topic="learner.state.changed",
                        payload={
                            "schema_version": 1,
                            "event_id": str(event_id),
                            "learner_id": str(request.learner_id),
                            "aggregate_version": next_version,
                            "event_type": request.event_type,
                        },
                        created_at=request.occurred_at,
                        available_at=request.occurred_at,
                        published_at=None,
                        attempts=0,
                        last_error_code=None,
                    )
                )
                return StoredLearnerState(
                    account_id=request.account_id,
                    learner_id=request.learner_id,
                    version=next_version,
                    state=request.state,
                    updated_at=request.occurred_at,
                )
        except IntegrityError as error:
            recovered = await self._recover_idempotent(request, command_hash)
            if recovered is not None:
                return recovered
            if _is_task_exposure_collision(error):
                raise TaskExposureConflictError from error
            raise LearnerStateConflictError from error
        except LearnerStateConflictError:
            recovered = await self._recover_idempotent(request, command_hash)
            if recovered is not None:
                return recovered
            raise
        except IdempotencyConflictError:
            raise
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error

    async def _recover_idempotent(
        self,
        request: LearnerStateCommit,
        command_hash: str,
    ) -> StoredLearnerState | None:
        try:
            async with self._engine.connect() as connection:
                existing = await _find_idempotent(
                    connection,
                    account_id=request.account_id,
                    idempotency_key=request.idempotency_key,
                )
        except SQLAlchemyError as error:
            raise PersistenceUnavailableError from error
        if existing is None:
            return None
        return _idempotent_result(existing, command_hash)


async def _write_snapshot(connection: AsyncConnection, request: LearnerStateCommit) -> int:
    state_payload = request.state.model_dump(mode="json")
    if request.expected_version is None:
        await connection.execute(
            insert(learner_states).values(
                learner_id=request.learner_id,
                account_id=request.account_id,
                version=0,
                state=state_payload,
                created_at=request.occurred_at,
                updated_at=request.occurred_at,
            )
        )
        return 0

    next_version = request.expected_version + 1
    result = await connection.execute(
        update(learner_states)
        .where(
            learner_states.c.account_id == request.account_id,
            learner_states.c.learner_id == request.learner_id,
            learner_states.c.version == request.expected_version,
        )
        .values(
            version=next_version,
            state=state_payload,
            updated_at=request.occurred_at,
        )
    )
    if result.rowcount != 1:
        raise LearnerStateConflictError
    return next_version


async def _existing_exposure(
    connection: AsyncConnection,
    *,
    instance_id: str,
) -> RowMapping | None:
    result = await connection.execute(
        select(
            task_exposures.c.account_id,
            task_exposures.c.learner_id,
            task_exposures.c.instance_id,
            task_exposures.c.blueprint_id,
            task_exposures.c.semantic_signature,
            task_exposures.c.semantic_fingerprint,
            task_exposures.c.instance_contract_hash,
        ).where(task_exposures.c.instance_id == instance_id)
    )
    return result.mappings().one_or_none()


def _matches_existing_exposure(
    existing: RowMapping,
    *,
    request: LearnerStateCommit,
    blueprint_id: str,
    semantic_signature: str,
    semantic_fingerprint: str,
    instance_contract_hash: str,
) -> bool:
    return (
        str(existing["account_id"]) == request.account_id
        and existing["learner_id"] == request.learner_id
        and str(existing["blueprint_id"]) == blueprint_id
        and str(existing["semantic_signature"]) == semantic_signature
        and str(existing["semantic_fingerprint"]) == semantic_fingerprint
        and str(existing["instance_contract_hash"]) == instance_contract_hash
    )


async def _write_task_exposures(
    connection: AsyncConnection,
    request: LearnerStateCommit,
) -> None:
    active = next(
        (
            item
            for item in request.state.plan_versions
            if item.plan_version_id == request.state.active_plan_version_id
        ),
        None,
    )
    if active is None:
        return
    for exposure in active.task_exposures:
        existing = await _existing_exposure(connection, instance_id=exposure.instance_id)
        if existing is not None:
            if _matches_existing_exposure(
                existing,
                request=request,
                blueprint_id=exposure.blueprint_id,
                semantic_signature=exposure.semantic_signature,
                semantic_fingerprint=exposure.semantic_fingerprint,
                instance_contract_hash=exposure.instance_contract_hash,
            ):
                continue
            raise TaskExposureConflictError

        # Insert the privacy-preserving tombstone first and do not suppress its uniqueness error.
        # That makes a concurrent or post-deletion reuse fail closed even when personal rows no
        # longer exist.
        await connection.execute(
            insert(task_collision_fingerprints).values(
                id=uuid5(
                    NAMESPACE_URL,
                    f"task-collision:{exposure.blueprint_id}:{exposure.semantic_signature}",
                ),
                item_family_id=exposure.item_family_id,
                blueprint_id=exposure.blueprint_id,
                semantic_signature=exposure.semantic_signature,
                semantic_fingerprint=exposure.semantic_fingerprint,
                semantic_tokens=list(exposure.semantic_tokens),
                served_at=datetime.fromisoformat(exposure.served_at),
            )
        )
        await connection.execute(
            insert(task_exposures).values(
                id=uuid5(NAMESPACE_URL, f"task-exposure:{exposure.instance_id}"),
                account_id=request.account_id,
                learner_id=request.learner_id,
                instance_id=exposure.instance_id,
                item_family_id=exposure.item_family_id,
                item_family_version=exposure.item_family_version,
                blueprint_id=exposure.blueprint_id,
                blueprint_version=exposure.blueprint_version,
                rubric_version=exposure.rubric_version,
                plan_version_id=exposure.plan_version_id,
                semantic_signature=exposure.semantic_signature,
                semantic_fingerprint=exposure.semantic_fingerprint,
                semantic_tokens=list(exposure.semantic_tokens),
                instance_contract_hash=exposure.instance_contract_hash,
                high_stakes_eligible=exposure.high_stakes_eligible,
                served_at=datetime.fromisoformat(exposure.served_at),
            )
        )


async def _find_idempotent(
    connection: AsyncConnection,
    *,
    account_id: str,
    idempotency_key: str,
) -> RowMapping | None:
    result = await connection.execute(
        select(
            learner_events.c.account_id,
            learner_events.c.learner_id,
            learner_events.c.aggregate_version,
            learner_events.c.command_hash,
            learner_events.c.state,
            learner_events.c.occurred_at,
        ).where(
            learner_events.c.account_id == account_id,
            learner_events.c.idempotency_key == idempotency_key,
        )
    )
    return result.mappings().one_or_none()


def _is_task_exposure_collision(error: IntegrityError) -> bool:
    diagnostics = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostics, "constraint_name", None)
    return constraint_name in {
        "uq_task_exposures_instance_id",
        "uq_task_exposures_blueprint_semantic",
        "uq_task_collision_fingerprints_blueprint_semantic",
        "pk_task_collision_fingerprints",
    }


def _idempotent_result(row: RowData, command_hash: str) -> StoredLearnerState:
    if row["command_hash"] != command_hash:
        raise IdempotencyConflictError
    return _stored_state(
        {
            "account_id": row["account_id"],
            "learner_id": row["learner_id"],
            "version": row["aggregate_version"],
            "state": row["state"],
            "updated_at": row["occurred_at"],
        }
    )


def _stored_state(row: RowData) -> StoredLearnerState:
    try:
        state = LearnerState.model_validate(row["state"])
    except ValidationError as error:
        raise PersistenceUnavailableError from error
    return StoredLearnerState(
        account_id=str(row["account_id"]),
        learner_id=row["learner_id"],
        version=int(row["version"]),
        state=state,
        updated_at=row["updated_at"],
    )


def _command_hash(request: LearnerStateCommit) -> str:
    payload = {
        "account_id": request.account_id,
        "learner_id": str(request.learner_id),
        "expected_version": request.expected_version,
        "event_type": request.event_type,
        "state": request.state.model_dump(mode="json"),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
