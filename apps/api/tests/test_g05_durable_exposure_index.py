from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.blueprint_service import EvidenceRubricMismatchError
from ai_learning_platform_api.learning.schemas import (
    CollisionFingerprintView,
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TaskExposureView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import SignedStateCodec
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    StoredLearnerState,
    TaskExposureConflictError,
)
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository
from ai_learning_platform_api.persistence.schemas import PersistentPlanImportRequest
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g05-durable-index-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _fingerprint(exposure: TaskExposureView) -> CollisionFingerprintView:
    return CollisionFingerprintView(
        item_family_id=exposure.item_family_id,
        blueprint_id=exposure.blueprint_id,
        semantic_fingerprint=exposure.semantic_fingerprint,
        semantic_signature=exposure.semantic_signature,
        semantic_tokens=list(exposure.semantic_tokens),
        served_at=exposure.served_at,
    )


class ExposureRepository:
    def __init__(self, *exposures: CollisionFingerprintView) -> None:
        self.exposures = exposures
        self.calls: list[tuple[str, ...]] = []

    async def list_task_collision_fingerprints(
        self,
        *,
        item_family_ids: tuple[str, ...],
    ) -> tuple[CollisionFingerprintView, ...]:
        self.calls.append(item_family_ids)
        return self.exposures


class NoopStateRepository:
    async def load(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        del account_id, learner_id
        return None

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        raise AssertionError(f"unexpected commit: {request.event_type}")

    async def delete_account(self, *, account_id: str) -> bool:
        del account_id
        return False


def _persistent_service(exposure_repository: ExposureRepository) -> PersistentLearningService:
    return PersistentLearningService(
        secret=_SECRET,
        repository=cast(Any, NoopStateRepository()),
        exposure_repository=exposure_repository,
        clock=lambda: _NOW,
    )


def test_persistent_service_rebinds_a_forced_cross_learner_collision() -> None:
    core = LearningPlanService(_SECRET)
    plan = core.create_plan(PlanRequest(learner_name="Cohort Learner", weekly_hours=4))
    first = plan.active_plan_version.task_exposures[0]
    exposure_repository = ExposureRepository(_fingerprint(first))

    rebound = asyncio.run(_persistent_service(exposure_repository)._deduplicate_new_plan(plan))

    assert exposure_repository.calls
    assert (
        rebound.active_plan_version.task_exposures[0].semantic_signature != first.semantic_signature
    )
    assert rebound.active_plan_version.activities[0].id != plan.active_plan_version.activities[0].id
    assert set(rebound.active_plan_version.delta.added_activity_ids) == {
        item.id for item in rebound.active_plan_version.activities
    }


def test_collision_rebind_recomputes_delta_against_previous_plan() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    initial = core.create_plan(PlanRequest(learner_name="Delta Learner", weekly_hours=4))
    replanned = core.replan(
        ReplanRequest(
            state_token=initial.state_token,
            weekly_hours=4,
            focus_competency_ids=[],
        )
    )
    collision = _fingerprint(replanned.active_plan_version.task_exposures[0])
    rebound = asyncio.run(
        _persistent_service(ExposureRepository(collision))._deduplicate_new_plan(replanned)
    )

    previous = next(
        item
        for item in rebound.plan_history
        if item.plan_version_id == rebound.active_plan_version.delta.previous_plan_version_id
    )
    previous_ids = {item.id for item in previous.activities}
    current_ids = [item.id for item in rebound.active_plan_version.activities]
    assert rebound.active_plan_version.delta.added_activity_ids == [
        item for item in current_ids if item not in previous_ids
    ]
    assert all(item in current_ids for item in rebound.active_plan_version.delta.added_activity_ids)


def test_collision_rebind_preserves_delayed_review_outside_active_snapshot() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name="Review Learner", weekly_hours=2))
    activity = plan.current_activity
    assert activity is not None
    progressed = core.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Completed every learner-specific criterion and recorded verification.",
            evidence_reference="repo://review-preservation",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    review_ids = {
        item.id
        for item in SignedStateCodec(_SECRET).decode(progressed.state_token).activities
        if item.kind == "review"
    }
    assert review_ids
    collision = _fingerprint(progressed.active_plan_version.task_exposures[0])

    rebound = asyncio.run(
        _persistent_service(ExposureRepository(collision))._deduplicate_new_plan(progressed)
    )
    rebound_state = SignedStateCodec(_SECRET).decode(rebound.state_token)
    assert review_ids.issubset({item.id for item in rebound_state.activities})


def test_evaluator_uses_immutable_source_contract_after_plan_history_pruning() -> None:
    service = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = service.create_plan(PlanRequest(learner_name="Pruned Provenance", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Implemented, tested, debugged, and explained the behavior independently.",
            evidence_reference="repo://evidence/pruned-provenance",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = progressed.evidence_history[-1]
    assert evidence.source_rubric_version == activity.rubric_version
    assert evidence.source_item_family_id == activity.item_family_id
    assert evidence.source_item_family_version == activity.item_family_version
    assert evidence.source_blueprint_id == activity.blueprint_id
    assert evidence.source_blueprint_version == activity.blueprint_version
    assert evidence.source_blueprint_approval_id == activity.blueprint_approval_id
    assert evidence.source_instance_contract_hash == activity.instance_contract_hash
    assert evidence.source_high_stakes_eligible is True

    current = progressed
    for _ in range(5):
        current = service.replan(
            ReplanRequest(
                state_token=current.state_token,
                weekly_hours=current.weekly_hours,
                focus_competency_ids=[],
            )
        )
    assert activity.id not in {
        item.id for version in current.plan_history for item in version.activities
    }

    wrong = TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="trusted-evaluator",
        evaluator_version="v1",
        rubric_version="wrong-rubric",
        instance_contract_hash=evidence.source_instance_contract_hash,
        confidence=95,
    )
    with pytest.raises(EvidenceRubricMismatchError):
        service.evaluate_evidence(state_token=current.state_token, verdict=wrong)

    accepted = service.evaluate_evidence(
        state_token=current.state_token,
        verdict=wrong.model_copy(update={"rubric_version": evidence.source_rubric_version}),
    )
    state = SignedStateCodec(_SECRET).decode(accepted.state_token)
    competency = next(
        item
        for item in state.competency_evidence.values()
        if item.competency_id == evidence.competency_id
    )
    assert competency.status == "independent"


def test_postgres_index_fails_closed_and_tombstone_survives_account_deletion() -> None:
    database_url = os.environ.get("AI_PLATFORM_DATABASE_URL")
    if database_url is None:
        pytest.skip("CI database URL is required for the G05 PostgreSQL integration test")

    async def scenario() -> None:
        runtime = DatabaseRuntime.create(database_url)
        repository = PostgresLearnerStateRepository(runtime.engine)
        codec = SignedStateCodec(_SECRET)
        core = LearningPlanService(_SECRET, clock=lambda: _NOW)
        account_a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        account_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        try:
            first_plan = core.create_plan(PlanRequest(learner_name="Database A", weekly_hours=4))
            first_state = codec.decode(first_plan.state_token)
            first = first_plan.active_plan_version.task_exposures[0]
            await repository.commit(
                LearnerStateCommit(
                    account_id=account_a,
                    learner_id=UUID(first_state.learner_id),
                    expected_version=None,
                    idempotency_key="g05-db-first",
                    event_type="test.g05.first",
                    state=first_state,
                    occurred_at=_NOW,
                )
            )
            indexed = await repository.list_task_collision_fingerprints(
                item_family_ids=(first.item_family_id,)
            )
            assert any(item.semantic_signature == first.semantic_signature for item in indexed)

            second_plan = core.create_plan(PlanRequest(learner_name="Database B", weekly_hours=4))
            second_state = codec.decode(second_plan.state_token)
            active = next(
                item
                for item in second_state.plan_versions
                if item.plan_version_id == second_state.active_plan_version_id
            )
            collision = active.task_exposures[0].model_copy(
                update={
                    "blueprint_id": first.blueprint_id,
                    "semantic_signature": first.semantic_signature,
                    "semantic_fingerprint": first.semantic_fingerprint,
                }
            )
            poisoned_active = active.model_copy(update={"task_exposures": [collision]})
            poisoned_state = second_state.model_copy(
                update={
                    "plan_versions": [
                        poisoned_active if item.plan_version_id == active.plan_version_id else item
                        for item in second_state.plan_versions
                    ]
                }
            )
            request = LearnerStateCommit(
                account_id=account_b,
                learner_id=UUID(poisoned_state.learner_id),
                expected_version=None,
                idempotency_key="g05-db-collision",
                event_type="test.g05.collision",
                state=poisoned_state,
                occurred_at=_NOW,
            )
            with pytest.raises(TaskExposureConflictError):
                await repository.commit(request)

            assert await repository.delete_account(account_id=account_a) is True
            after_deletion = await repository.list_task_collision_fingerprints(
                item_family_ids=(first.item_family_id,)
            )
            assert any(
                item.semantic_signature == first.semantic_signature for item in after_deletion
            )
            with pytest.raises(TaskExposureConflictError):
                await repository.commit(request)
        finally:
            await repository.delete_account(account_id=account_a)
            await repository.delete_account(account_id=account_b)
            await runtime.shutdown()

    asyncio.run(scenario())


def test_browser_import_fails_closed_without_rebinding_served_work() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name="Browser Import", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = core.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Completed the already-served browser task before import.",
            evidence_reference="repo://browser-import",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    collision = _fingerprint(progressed.active_plan_version.task_exposures[0])
    service = _persistent_service(ExposureRepository(collision))

    with pytest.raises(TaskExposureConflictError):
        asyncio.run(
            service.import_plan(
                account_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                request=PersistentPlanImportRequest(
                    idempotency_key="g05-browser-import-0001",
                    state_token=progressed.state_token,
                ),
            )
        )

    resumed = core.resume(progressed.state_token)
    assert resumed.state_token == progressed.state_token
    assert resumed.evidence_history[-1].source_plan_version_id == (
        progressed.evidence_history[-1].source_plan_version_id
    )
