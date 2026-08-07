"""Tests for persistence-independent durable learning orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ai_learning_platform_api.learning.schemas import AssessmentAnswer
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.schemas import (
    PersistentAssessmentStartRequest,
    PersistentAssessmentSubmitRequest,
    PersistentPlanCreateRequest,
    PersistentPlanImportRequest,
    PersistentProgressRequest,
    PersistentReplanRequest,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "test-persistence-secret-with-more-than-thirty-two-bytes"
_ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
_NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


class MemoryRepository:
    """Deterministic test repository with optimistic version checks."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, UUID], StoredLearnerState] = {}
        self.idempotent: dict[tuple[str, str], StoredLearnerState] = {}

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return self.values.get((account_id, learner_id))

    async def delete_account(self, *, account_id: str) -> bool:
        identities = [identity for identity in self.values if identity[0] == account_id]
        for identity in identities:
            del self.values[identity]
        idempotency_keys = [identity for identity in self.idempotent if identity[0] == account_id]
        for identity in idempotency_keys:
            del self.idempotent[identity]
        return bool(identities)

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        idempotency_identity = (request.account_id, request.idempotency_key)
        previous_result = self.idempotent.get(idempotency_identity)
        if previous_result is not None:
            return previous_result

        identity = (request.account_id, request.learner_id)
        current = self.values.get(identity)
        if request.expected_version is None:
            if current is not None:
                raise LearnerStateConflictError
            next_version = 0
        else:
            if current is None or current.version != request.expected_version:
                raise LearnerStateConflictError
            next_version = current.version + 1
        stored = StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=next_version,
            state=request.state,
            updated_at=request.occurred_at,
        )
        self.values[identity] = stored
        self.idempotent[idempotency_identity] = stored
        return stored


def _service(repository: MemoryRepository) -> PersistentLearningService:
    return PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        clock=lambda: _NOW,
    )


def _create_request(key: str = "create-command-0001") -> PersistentPlanCreateRequest:
    return PersistentPlanCreateRequest(
        idempotency_key=key,
        learner_name="Mahmoud",
        weekly_hours=8,
        experience_summary="Embedded engineer transitioning to backend development",
        ratings=[],
    )


def test_full_durable_learning_cycle() -> None:
    repository = MemoryRepository()
    service = _service(repository)

    created = asyncio.run(service.create_plan(account_id=_ACCOUNT_ID, request=_create_request()))
    assert created.version == 0
    assert created.plan.learner_name == "Mahmoud"
    learner_id = UUID(created.plan.learner_id)

    resumed = asyncio.run(service.resume_plan(account_id=_ACCOUNT_ID, learner_id=learner_id))
    assert resumed == created

    current_activity = created.plan.current_activity
    assert current_activity is not None
    progressed = asyncio.run(
        service.complete_activity(
            account_id=_ACCOUNT_ID,
            request=PersistentProgressRequest(
                learner_id=learner_id,
                expected_version=0,
                idempotency_key="progress-command-0001",
                activity_id=current_activity.id,
                reflection="Implemented and tested the required behavior.",
                evidence_reference="repository/commit/abc123",
                criteria_met=list(current_activity.acceptance_criteria),
                confidence=3,
            ),
        )
    )
    assert progressed.version == 1
    assert progressed.plan.completed_count == 1

    replanned = asyncio.run(
        service.replan(
            account_id=_ACCOUNT_ID,
            request=PersistentReplanRequest(
                learner_id=learner_id,
                expected_version=1,
                idempotency_key="replan-command-0001",
                weekly_hours=12,
                focus_competency_ids=[progressed.plan.priority_competencies[0].id],
            ),
        )
    )
    assert replanned.version == 2
    assert replanned.plan.weekly_hours == 12

    attempt_view = asyncio.run(
        service.start_assessment(
            account_id=_ACCOUNT_ID,
            request=PersistentAssessmentStartRequest(
                learner_id=learner_id,
                question_count=2,
            ),
        )
    )
    answers = [
        AssessmentAnswer(question_id=question.id, option_id=question.options[0].id)
        for question in attempt_view.attempt.questions
    ]
    submitted = asyncio.run(
        service.submit_assessment(
            account_id=_ACCOUNT_ID,
            request=PersistentAssessmentSubmitRequest(
                learner_id=learner_id,
                expected_version=2,
                idempotency_key="assessment-command-0001",
                attempt_token=attempt_view.attempt.attempt_token,
                answers=answers,
            ),
        )
    )
    assert submitted.version == 3
    assert submitted.submission.plan.sequence > replanned.plan.sequence


def test_delete_account_removes_only_owned_memory_state() -> None:
    repository = MemoryRepository()
    service = _service(repository)
    created = asyncio.run(service.create_plan(account_id=_ACCOUNT_ID, request=_create_request()))
    learner_id = UUID(created.plan.learner_id)

    assert asyncio.run(service.delete_account(account_id=_ACCOUNT_ID)) is True
    assert asyncio.run(service.delete_account(account_id=_ACCOUNT_ID)) is False
    assert repository.values == {}
    assert repository.idempotent == {}
    with pytest.raises(LearnerStateNotFoundError):
        asyncio.run(service.resume_plan(account_id=_ACCOUNT_ID, learner_id=learner_id))


def test_imports_valid_signed_state_and_is_idempotent() -> None:
    source_repository = MemoryRepository()
    source_service = _service(source_repository)
    source = asyncio.run(
        source_service.create_plan(
            account_id=_ACCOUNT_ID,
            request=_create_request("source-create-command"),
        )
    )

    target_repository = MemoryRepository()
    target_service = _service(target_repository)
    request = PersistentPlanImportRequest(
        idempotency_key="import-command-0001",
        state_token=source.plan.state_token,
    )
    first = asyncio.run(target_service.import_plan(account_id=_ACCOUNT_ID, request=request))
    second = asyncio.run(target_service.import_plan(account_id=_ACCOUNT_ID, request=request))

    assert first == second
    assert first.version == 0


def test_rejects_stale_version_and_cross_account_resume() -> None:
    repository = MemoryRepository()
    service = _service(repository)
    created = asyncio.run(service.create_plan(account_id=_ACCOUNT_ID, request=_create_request()))
    learner_id = UUID(created.plan.learner_id)
    activity = created.plan.current_activity
    assert activity is not None

    with pytest.raises(LearnerStateConflictError):
        asyncio.run(
            service.complete_activity(
                account_id=_ACCOUNT_ID,
                request=PersistentProgressRequest(
                    learner_id=learner_id,
                    expected_version=7,
                    idempotency_key="stale-progress-command",
                    activity_id=activity.id,
                ),
            )
        )

    with pytest.raises(LearnerStateNotFoundError):
        asyncio.run(
            service.resume_plan(
                account_id="22222222-2222-4222-8222-222222222222",
                learner_id=learner_id,
            )
        )
