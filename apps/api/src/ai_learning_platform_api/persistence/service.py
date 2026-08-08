"""Durable orchestration around the deterministic signed-state learning engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.schemas import (
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
)
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    LearnerStateRepository,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.schemas import (
    PersistentAssessmentAttemptView,
    PersistentAssessmentStartRequest,
    PersistentAssessmentSubmissionView,
    PersistentAssessmentSubmitRequest,
    PersistentPlanCreateRequest,
    PersistentPlanImportRequest,
    PersistentPlanView,
    PersistentProgressRequest,
    PersistentReplanRequest,
)

Clock = Callable[[], datetime]


class PersistentLearningService:
    """Make PostgreSQL authoritative without moving decision logic into infrastructure."""

    def __init__(
        self,
        *,
        secret: str,
        repository: LearnerStateRepository,
        clock: Clock | None = None,
    ) -> None:
        self._core = LearningPlanService(secret)
        self._codec = SignedStateCodec(secret)
        self._repository = repository
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
        state = self._codec.decode(plan.state_token).model_copy(update={"storage_mode": "durable"})
        stored = await self._repository.commit(
            LearnerStateCommit(
                account_id=account_id,
                learner_id=UUID(state.learner_id),
                expected_version=None,
                idempotency_key=request.idempotency_key,
                event_type="learner.plan.created",
                state=state,
                occurred_at=self._now(),
            )
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
        normalized = self._core.resume(request.state_token)
        state = self._codec.decode(normalized.state_token).model_copy(update={"storage_mode": "durable"})
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
        """Delete the current anonymous durable account and all database-owned history."""
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
        return await self._commit_plan(
            account_id=account_id,
            stored=stored,
            state_token=plan.state_token,
            idempotency_key=request.idempotency_key,
            event_type="learner.plan.replanned",
        )

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
        committed = await self._repository.commit(
            LearnerStateCommit(
                account_id=account_id,
                learner_id=stored.learner_id,
                expected_version=stored.version,
                idempotency_key=request.idempotency_key,
                event_type="learner.assessment.submitted",
                state=self._codec.decode(submission.plan.state_token),
                occurred_at=self._now(),
            )
        )
        return PersistentAssessmentSubmissionView(
            submission=submission.model_copy(update={"plan": self._view(committed).plan}),
            version=committed.version,
        )

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
