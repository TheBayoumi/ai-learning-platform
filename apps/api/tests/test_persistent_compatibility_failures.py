"""Failure and migration tests for the durable compatibility boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Never
from uuid import UUID

import pytest
from fastapi import HTTPException

from ai_learning_platform_api.learning.schemas import PlanRequest, ResumeRequest
from ai_learning_platform_api.learning.service import LearningPlanError, LearningPlanService
from ai_learning_platform_api.persistence.contracts import (
    IdempotencyConflictError,
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.transport.http.persistent_compatibility import (
    PersistentCompatibilityService,
    _run,
    _uuid,
)

_SIGNING_KEY = "compatibility-failures-" + ("x" * 32)
_ACCOUNT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_NOW = datetime(2026, 7, 24, 15, 0, tzinfo=UTC)


class MemoryRepository:
    """Minimal repository for one-time legacy state import."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, UUID], StoredLearnerState] = {}

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return self.values.get((account_id, learner_id))

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        stored = StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=0 if request.expected_version is None else request.expected_version + 1,
            state=request.state,
            updated_at=request.occurred_at,
        )
        self.values[(request.account_id, request.learner_id)] = stored
        return stored


def test_resume_imports_a_valid_legacy_signed_state_once() -> None:
    legacy = LearningPlanService(_SIGNING_KEY).create_plan(
        PlanRequest(learner_name="Legacy Learner", ratings=[])
    )
    repository = MemoryRepository()
    persistent = PersistentLearningService(
        secret=_SIGNING_KEY,
        repository=repository,
        clock=lambda: _NOW,
    )
    compatibility = PersistentCompatibilityService(
        secret=_SIGNING_KEY,
        persistent=persistent,
    )

    imported = asyncio.run(
        compatibility.resume_plan(
            account_id=_ACCOUNT_ID,
            command_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            request=ResumeRequest(state_token=legacy.state_token),
        )
    )
    resumed = asyncio.run(
        compatibility.resume_plan(
            account_id=_ACCOUNT_ID,
            command_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            request=ResumeRequest(state_token=legacy.state_token),
        )
    )

    assert imported == resumed
    assert imported.learner_name == "Legacy Learner"
    assert len(repository.values) == 1
    assert compatibility.list_roles()


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (LearnerStateNotFoundError(), 404, "LEARNER_STATE_NOT_FOUND"),
        (LearnerStateConflictError(), 409, "LEARNER_STATE_CONFLICT"),
        (IdempotencyConflictError(), 409, "LEARNER_STATE_CONFLICT"),
        (PersistenceUnavailableError(), 503, "PERSISTENCE_UNAVAILABLE"),
        (LearningPlanError(), 400, "LEARNING_PLAN_ERROR"),
    ],
)
def test_transport_maps_safe_failures(
    error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    async def operation() -> Never:
        raise error

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_run(operation))

    assert captured.value.status_code == expected_status
    assert isinstance(captured.value.detail, dict)
    assert captured.value.detail["code"] == expected_code


def test_request_context_uuid_is_canonicalized_and_rejects_invalid_values() -> None:
    assert _uuid("BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB") == _ACCOUNT_ID

    with pytest.raises(HTTPException) as captured:
        _uuid("invalid")

    assert captured.value.status_code == 400
    assert isinstance(captured.value.detail, dict)
    assert captured.value.detail["code"] == "INVALID_REQUEST_CONTEXT"
