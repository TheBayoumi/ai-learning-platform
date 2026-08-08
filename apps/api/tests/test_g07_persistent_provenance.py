from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.schemas import (
    ArtifactCheckpointView,
    PlanRequest,
    ProgressRequest,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceSubmission,
)
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit, StoredLearnerState
from ai_learning_platform_api.persistence.schemas import (
    PersistentWorkProvenanceEvaluationRequest,
    PersistentWorkProvenanceSubmissionRequest,
    PersistentWorkVerificationRequest,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g07-persistent-provenance-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
_ACCOUNT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class MemoryRepository:
    def __init__(self, stored: StoredLearnerState) -> None:
        self.stored = stored
        self.commits: list[LearnerStateCommit] = []

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        if account_id == self.stored.account_id and learner_id == self.stored.learner_id:
            return self.stored
        return None

    async def delete_account(self, *, account_id: str) -> bool:
        del account_id
        return False

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        self.commits.append(request)
        self.stored = StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=self.stored.version + 1,
            state=request.state,
            updated_at=request.occurred_at,
        )
        return self.stored


def test_provenance_challenge_capture_and_review_append_durable_events() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name="Durable Provenance", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    completed = core.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection=(
                "I completed the learner-specific task and recorded the design reasoning needed "
                "for later provenance and defense verification."
            ),
            evidence_reference="repo://g07-durable",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = completed.evidence_history[-1]
    state = core._codec.decode(completed.state_token).model_copy(update={"storage_mode": "durable"})
    repository = MemoryRepository(
        StoredLearnerState(
            account_id=_ACCOUNT,
            learner_id=UUID(state.learner_id),
            version=10,
            state=state,
            updated_at=_NOW,
        )
    )
    persistent = PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        clock=lambda: _NOW,
    )

    issued = asyncio.run(
        persistent.issue_work_verification(
            account_id=_ACCOUNT,
            request=PersistentWorkVerificationRequest(
                learner_id=UUID(state.learner_id),
                expected_version=10,
                idempotency_key="g07-work-challenge-0001",
                evidence_id=evidence.evidence_id,
            ),
        )
    )
    record = issued.plan.work_provenance[-1]
    challenge_ids = {item.kind: item.challenge_id for item in record.challenges}
    assert repository.commits[-1].event_type == "learner.work.verification_issued"

    submitted = asyncio.run(
        persistent.submit_work_provenance(
            account_id=_ACCOUNT,
            request=PersistentWorkProvenanceSubmissionRequest(
                learner_id=UUID(state.learner_id),
                expected_version=11,
                idempotency_key="g07-work-capture-0001",
                submission=WorkProvenanceSubmission(
                    evidence_id=evidence.evidence_id,
                    artifact_id="durable-artifact",
                    final_artifact_sha256="2" * 64,
                    checkpoints=[
                        ArtifactCheckpointView(
                            checkpoint_id="durable-cp-1",
                            artifact_sha256="1" * 64,
                            parent_checkpoint_id="",
                            created_at=_NOW.isoformat(),
                            change_summary="Initial implementation.",
                            toolchain=["python", "git"],
                            assistance="none",
                        ),
                        ArtifactCheckpointView(
                            checkpoint_id="durable-cp-2",
                            artifact_sha256="2" * 64,
                            parent_checkpoint_id="durable-cp-1",
                            created_at=(_NOW + timedelta(hours=1)).isoformat(),
                            change_summary="Hidden modification and debugging revision.",
                            toolchain=["python", "git", "pytest"],
                            assistance="none",
                        ),
                    ],
                    assistance_disclosure="none",
                    source_attribution="Self-authored; project documentation consulted.",
                    modification_challenge_id=challenge_ids["modification"],
                    modification_evidence_reference="repo://durable/modification",
                    debugging_challenge_id=challenge_ids["debugging"],
                    debugging_evidence_reference="repo://durable/debugging",
                    defense_challenge_id=challenge_ids["defense"],
                    defense_response=(
                        "I chose deterministic state ownership because it preserves replay and "
                        "isolation. I rejected provider-owned state because failures could "
                        "silently change evidence authority, and I verified the correction "
                        "with focused tests."
                    ),
                ),
            ),
        )
    )
    assert submitted.version == 12
    assert repository.commits[-1].event_type == "learner.work.provenance_captured"

    reviewed = asyncio.run(
        persistent.evaluate_work_provenance(
            account_id=_ACCOUNT,
            request=PersistentWorkProvenanceEvaluationRequest(
                learner_id=UUID(state.learner_id),
                expected_version=12,
                idempotency_key="g07-work-review-0001",
                verdict=TrustedWorkProvenanceVerdict(
                    evidence_id=evidence.evidence_id,
                    artifact_id="durable-artifact",
                    disposition="accepted",
                    authorship_verified=True,
                    modification_verified=True,
                    debugging_verified=True,
                    defense_verified=True,
                    evaluator_id="durable-work-reviewer",
                    evaluator_version="v1",
                    confidence=96,
                ),
            ),
        )
    )
    assert reviewed.version == 13
    assert repository.commits[-1].event_type == "learner.work.provenance_evaluated"
    assert reviewed.plan.work_provenance[-1].eligible_for_readiness is True
