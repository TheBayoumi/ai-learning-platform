"""Persistence-independent contracts for durable learner state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ai_learning_platform_api.learning.schemas import CollisionFingerprintView, LearnerState

_MAX_ACCOUNT_ID_LENGTH = 160
_MAX_IDEMPOTENCY_KEY_LENGTH = 160
_MAX_EVENT_TYPE_LENGTH = 120


class PersistenceError(RuntimeError):
    """Base class for persistence failures safe to classify at orchestration boundaries."""


class PersistenceUnavailableError(PersistenceError):
    """The configured persistence backend cannot complete the operation."""


class LearnerStateNotFoundError(PersistenceError):
    """No durable learner aggregate belongs to the supplied account and identifier."""


class LearnerStateConflictError(PersistenceError):
    """The aggregate version changed before the requested commit completed."""


class TaskExposureConflictError(LearnerStateConflictError):
    """A served task collided with the durable cohort exposure index."""


class IdempotencyConflictError(PersistenceError):
    """An idempotency key was reused for a different command payload."""


class ReplayDivergenceError(PersistenceError):
    """The append-only event sequence cannot reproduce one contiguous aggregate."""


@dataclass(frozen=True, slots=True)
class StoredLearnerState:
    """One owned learner aggregate snapshot loaded from durable storage."""

    account_id: str
    learner_id: UUID
    version: int
    state: LearnerState
    updated_at: datetime

    def __post_init__(self) -> None:
        _validate_account_id(self.account_id)
        if self.version < 0:
            raise ValueError("version must be non-negative")
        _validate_aware_timestamp(self.updated_at, field_name="updated_at")
        _validate_learner_identity(self.learner_id, self.state)


@dataclass(frozen=True, slots=True)
class LearnerStateCommit:
    """Atomic state, event, idempotency, exposure-index, and outbox commit request."""

    account_id: str
    learner_id: UUID
    expected_version: int | None
    idempotency_key: str
    event_type: str
    state: LearnerState
    occurred_at: datetime

    def __post_init__(self) -> None:
        _validate_account_id(self.account_id)
        if self.expected_version is not None and self.expected_version < 0:
            raise ValueError("expected_version must be non-negative")
        _validate_bounded_token(
            self.idempotency_key,
            field_name="idempotency_key",
            max_length=_MAX_IDEMPOTENCY_KEY_LENGTH,
        )
        _validate_bounded_token(
            self.event_type,
            field_name="event_type",
            max_length=_MAX_EVENT_TYPE_LENGTH,
        )
        _validate_aware_timestamp(self.occurred_at, field_name="occurred_at")
        _validate_learner_identity(self.learner_id, self.state)


class LearnerStateRepository(Protocol):
    """Durable learner-state boundary implemented by PostgreSQL infrastructure."""

    async def load(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None: ...

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState: ...

    async def delete_account(self, *, account_id: str) -> bool: ...


class TaskExposureIndexRepository(Protocol):
    """Complete unlinkable cohort collision history used before serving new instances."""

    async def list_task_collision_fingerprints(
        self,
        *,
        item_family_ids: tuple[str, ...],
    ) -> tuple[CollisionFingerprintView, ...]: ...


class LearnerStateReplayRepository(Protocol):
    """Audit boundary for reconstructing an aggregate from append-only events."""

    async def replay(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None: ...


def validate_account_id(account_id: str) -> None:
    """Validate one canonical anonymous-account identifier at public boundaries."""
    _validate_account_id(account_id)


def _validate_account_id(account_id: str) -> None:
    _validate_bounded_token(
        account_id,
        field_name="account_id",
        max_length=_MAX_ACCOUNT_ID_LENGTH,
    )


def _validate_bounded_token(value: str, *, field_name: str, max_length: int) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical token")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds the maximum length")
    if any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must not contain whitespace")


def _validate_aware_timestamp(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_learner_identity(learner_id: UUID, state: LearnerState) -> None:
    try:
        state_learner_id = UUID(state.learner_id)
    except ValueError as error:
        raise ValueError("state learner_id must be a UUID") from error
    if state_learner_id != learner_id:
        raise ValueError("state learner_id does not match the aggregate learner_id")
