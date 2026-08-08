"""Durable orchestration around the deterministic signed-state learning engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.blueprints import collides
from ai_learning_platform_api.learning.schemas import (
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    CollisionFingerprintView,
    PlanRequest,
    PlanView,
    ProgressRequest,
    ReplanRequest,
)
from ai_learning_platform_api.learning.service import SignedStateCodec
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    LearnerStateRepository,
    StoredLearnerState,
    TaskExposureConflictError,
    TaskExposureIndexRepository,
)
from ai_learning_platform_api.persistence.schemas import (
    PersistentAssessmentAttemptView,
    PersistentAssessmentStartRequest,
    PersistentAssessmentSubmissionView,
    PersistentAssessmentSubmitRequest,
    PersistentEvidenceEvaluationRequest,
    PersistentPlanCreateRequest,
    PersistentPlanImportRequest,
    PersistentPlanView,
    PersistentProgressRequest,
    PersistentReplanRequest,
)

Clock = Callable[[], datetime]
_MAX_EXPOSURE_COMMIT_ATTEMPTS = 3


class PersistentLearningService:
    """Make PostgreSQL authoritative without moving decision logic into infrastructure."""

    def __init__(
        self,
        *,
        secret: str,
        repository: LearnerStateRepository,
        exposure_repository: TaskExposureIndexRepository | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._core = LearningPlanService(secret)
        self._codec = SignedStateCodec(secret)
        self._repository = repository
        self._exposure_repository = exposure_repository
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)

    async def create_plan(
        self,
        *,
        account_id: str,
        request: PersistentPlanCreateRequest,
    ) -> PersistentPlanView:
        plan = self._core.create_plan(
            PlanRequest(
                learner_name=request.learner_name,
                target_role=request.target_role,
                target=request.target,
                weekly_hours=request.weekly_hours,
                experience_summary=request.experience_summary,
                ratings=request.ratings,
            )
        )
        stored, _ = await self._commit_generated_plan(
            account_id=account_id,
            learner_id=UUID(plan.learner_id),
            expected_version=None,
            idempotency_key=request.idempotency_key,
            event_type="learner.plan.created",
            plan=plan,
        )
        return self._view(stored)

    async def import_plan(
        self,
        *,
        account_id: str,
        request: PersistentPlanImportRequest,
    ) -> PersistentPlanView:
        supplied_state = self._codec.decode(request.state_token)
        if supplied_state.storage_mode != "browser":
            raise LearnerStateNotFoundError
        plan = self._core.resume(request.state_token)
        # Import is a storage-mode transition, not a curriculum transition. Already-served
        # browser tasks and their evidence provenance must never be rewritten during import.
        await self._validate_import_exposures(plan)
        state = self._codec.decode(plan.state_token).model_copy(update={"storage_mode": "durable"})
        stored = await self._repository.commit(
            LearnerStateCommit(
                account_id=account_id,
                learner_id=UUID(state.learner_id),
                expected_version=None,
                idempotency_key=request.idempotency_key,
                event_type="learner.plan.imported",
                state=state,
                occurred_at=self._now(),
            )
        )
        return self._view(stored)

    async def resume_plan(self, *, account_id: str, learner_id: UUID) -> PersistentPlanView:
        stored = await self._load(account_id=account_id, learner_id=learner_id)
        return self._view(stored)

    async def delete_account(self, *, account_id: str) -> bool:
        """Delete personal history; repository-owned unlinkable collision tombstones remain."""
        return await self._repository.delete_account(account_id=account_id)

    async def complete_activity(
        self,
        *,
        account_id: str,
        request: PersistentProgressRequest,
    ) -> PersistentPlanView:
        stored = await self._load_expected(
            account_id=account_id,
            learner_id=request.learner_id,
            expected_version=request.expected_version,
        )
        # Completing an already-served task creates evidence/review state but no new build
        # instance, so cohort deduplication must not rebind the active task snapshot here.
        plan = self._core.complete_activity(
            ProgressRequest(
                state_token=self._codec.encode(stored.state),
                activity_id=request.activity_id,
                reflection=request.reflection,
                evidence_reference=request.evidence_reference,
                criteria_met=request.criteria_met,
                confidence=request.confidence,
            )
        )
        return await self._commit_plan(
            account_id=account_id,
            stored=stored,
            state_token=plan.state_token,
            idempotency_key=request.idempotency_key,
            event_type="learner.activity.completed",
        )

    async def evaluate_evidence(
        self,
        *,
        account_id: str,
        request: PersistentEvidenceEvaluationRequest,
    ) -> PersistentPlanView:
        """Commit one trusted evaluator verdict through the durable aggregate boundary."""
        stored = await self._load_expected(
            account_id=account_id,
            learner_id=request.learner_id,
            expected_version=request.expected_version,
        )
        plan = self._core.evaluate_evidence(
            state_token=self._codec.encode(stored.state),
            verdict=request.verdict,
        )
        if plan.sequence == stored.state.sequence:
            return self._view(stored)
        committed, _ = await self._commit_generated_plan(
            account_id=account_id,
            learner_id=stored.learner_id,
            expected_version=stored.version,
            idempotency_key=request.idempotency_key,
            event_type="learner.evidence.evaluated",
            plan=plan,
        )
        return self._view(committed)

    async def replan(
        self,
        *,
        account_id: str,
        request: PersistentReplanRequest,
    ) -> PersistentPlanView:
        stored = await self._load_expected(
            account_id=account_id,
            learner_id=request.learner_id,
            expected_version=request.expected_version,
        )
        plan = self._core.replan(
            ReplanRequest(
                state_token=self._codec.encode(stored.state),
                weekly_hours=request.weekly_hours,
                focus_competency_ids=request.focus_competency_ids,
            )
        )
        committed, _ = await self._commit_generated_plan(
            account_id=account_id,
            learner_id=stored.learner_id,
            expected_version=stored.version,
            idempotency_key=request.idempotency_key,
            event_type="learner.plan.replanned",
            plan=plan,
        )
        return self._view(committed)

    async def start_assessment(
        self,
        *,
        account_id: str,
        request: PersistentAssessmentStartRequest,
    ) -> PersistentAssessmentAttemptView:
        stored = await self._load(account_id=account_id, learner_id=request.learner_id)
        attempt = self._core.start_assessment(
            AssessmentStartRequest(
                state_token=self._codec.encode(stored.state),
                question_count=request.question_count,
            )
        )
        return PersistentAssessmentAttemptView(attempt=attempt)

    async def submit_assessment(
        self,
        *,
        account_id: str,
        request: PersistentAssessmentSubmitRequest,
    ) -> PersistentAssessmentSubmissionView:
        stored = await self._load_expected(
            account_id=account_id,
            learner_id=request.learner_id,
            expected_version=request.expected_version,
        )
        submission = self._core.submit_assessment(
            AssessmentSubmitRequest(
                state_token=self._codec.encode(stored.state),
                attempt_token=request.attempt_token,
                answers=request.answers,
            )
        )
        committed, committed_plan = await self._commit_generated_plan(
            account_id=account_id,
            learner_id=stored.learner_id,
            expected_version=stored.version,
            idempotency_key=request.idempotency_key,
            event_type="learner.assessment.submitted",
            plan=submission.plan,
        )
        return PersistentAssessmentSubmissionView(
            submission=submission.model_copy(
                update={
                    "plan": committed_plan.model_copy(
                        update={"state_token": self._codec.encode(committed.state)}
                    )
                }
            ),
            version=committed.version,
        )

    async def _collision_history(self, plan: PlanView) -> tuple[CollisionFingerprintView, ...]:
        if self._exposure_repository is None:
            return ()
        item_family_ids = tuple(
            sorted(
                {
                    item.item_family_id
                    for item in plan.active_plan_version.task_exposures
                    if item.item_family_id
                }
            )
        )
        if not item_family_ids:
            return ()
        return await self._exposure_repository.list_task_collision_fingerprints(
            item_family_ids=item_family_ids
        )

    async def _validate_import_exposures(self, plan: PlanView) -> None:
        """Fail closed instead of retroactively changing already-served browser tasks."""
        collisions = await self._collision_history(plan)
        if not collisions:
            return
        for exposure in plan.active_plan_version.task_exposures:
            if collides(
                semantic_fingerprint=exposure.semantic_fingerprint,
                semantic_signature=exposure.semantic_signature,
                semantic_tokens=exposure.semantic_tokens,
                exposures=collisions,
            ):
                raise TaskExposureConflictError

    async def _deduplicate_new_plan(self, plan: PlanView) -> PlanView:
        """Rebind newly generated builds against the complete unlinkable cohort history."""
        collisions = await self._collision_history(plan)
        if not collisions:
            return plan
        return self._core.rebind_external_exposures(
            state_token=plan.state_token,
            external_exposures=collisions,
        )

    async def _commit_generated_plan(
        self,
        *,
        account_id: str,
        learner_id: UUID,
        expected_version: int | None,
        idempotency_key: str,
        event_type: str,
        plan: PlanView,
    ) -> tuple[StoredLearnerState, PlanView]:
        """Reserve newly generated work with bounded reread/rebind retry on exposure races."""
        candidate = await self._deduplicate_new_plan(plan)
        for attempt in range(_MAX_EXPOSURE_COMMIT_ATTEMPTS):
            state = self._codec.decode(candidate.state_token).model_copy(
                update={"storage_mode": "durable"}
            )
            try:
                stored = await self._repository.commit(
                    LearnerStateCommit(
                        account_id=account_id,
                        learner_id=learner_id,
                        expected_version=expected_version,
                        idempotency_key=idempotency_key,
                        event_type=event_type,
                        state=state,
                        occurred_at=self._now(),
                    )
                )
                return stored, candidate
            except TaskExposureConflictError:
                if (
                    self._exposure_repository is None
                    or attempt + 1 >= _MAX_EXPOSURE_COMMIT_ATTEMPTS
                ):
                    raise
                # The conflicting transaction has become visible in the durable fingerprint
                # authority. Reread it, deterministically rebind the new plan, and retry the same
                # atomic command. Import/completion never enter this path.
                candidate = await self._deduplicate_new_plan(candidate)
        raise TaskExposureConflictError

    async def _commit_plan(
        self,
        *,
        account_id: str,
        stored: StoredLearnerState,
        state_token: str,
        idempotency_key: str,
        event_type: str,
    ) -> PersistentPlanView:
        committed = await self._repository.commit(
            LearnerStateCommit(
                account_id=account_id,
                learner_id=stored.learner_id,
                expected_version=stored.version,
                idempotency_key=idempotency_key,
                event_type=event_type,
                state=self._codec.decode(state_token),
                occurred_at=self._now(),
            )
        )
        return self._view(committed)

    async def _load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState:
        stored = await self._repository.load(account_id=account_id, learner_id=learner_id)
        if stored is None:
            raise LearnerStateNotFoundError
        return stored

    async def _load_expected(
        self,
        *,
        account_id: str,
        learner_id: UUID,
        expected_version: int,
    ) -> StoredLearnerState:
        stored = await self._load(account_id=account_id, learner_id=learner_id)
        if stored.version != expected_version:
            raise LearnerStateConflictError
        return stored

    def _view(self, stored: StoredLearnerState) -> PersistentPlanView:
        plan = self._core.resume(self._codec.encode(stored.state))
        return PersistentPlanView(plan=plan, version=stored.version)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value.astimezone(UTC)
