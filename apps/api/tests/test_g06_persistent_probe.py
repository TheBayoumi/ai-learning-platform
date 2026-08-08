from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.qualification_service import (
    QualificationLearningPlanService as LearningPlanService,
)
from ai_learning_platform_api.learning.schemas import (
    PlanRequest,
    ProgressRequest,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
)
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit, StoredLearnerState
from ai_learning_platform_api.persistence.schemas import PersistentProbeEvaluationRequest
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g06-persistent-probe-secret-with-more-than-thirty-two-bytes"
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


def test_trusted_probe_verdict_commits_a_versioned_durable_event() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name="Durable Probe", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    completed = core.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Completed and verified every exact task requirement.",
            evidence_reference="repo://g06-durable-probe",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = completed.evidence_history[-1]
    qualified = core.evaluate_evidence(
        state_token=completed.state_token,
        verdict=TrustedEvidenceVerdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            disposition="accepted",
            independence="independent",
            assistance="none",
            reasoning="verified",
            evaluator_id="g06-durable-evaluator",
            evaluator_version="v1",
            rubric_version=evidence.source_rubric_version,
            instance_contract_hash=evidence.source_instance_contract_hash,
            confidence=96,
        ),
    )
    transfer = next(
        item for item in qualified.verification_probes if item.verification_class == "transfer"
    )
    state = core._codec.decode(qualified.state_token).model_copy(update={"storage_mode": "durable"})
    repository = MemoryRepository(
        StoredLearnerState(
            account_id=_ACCOUNT,
            learner_id=UUID(state.learner_id),
            version=4,
            state=state,
            updated_at=_NOW,
        )
    )
    persistent = PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        clock=lambda: _NOW,
    )

    result = asyncio.run(
        persistent.evaluate_probe(
            account_id=_ACCOUNT,
            request=PersistentProbeEvaluationRequest(
                learner_id=UUID(state.learner_id),
                expected_version=4,
                idempotency_key="g06-probe-eval-0001",
                verdict=TrustedProbeVerdict(
                    probe_id=transfer.probe_id,
                    competency_id=transfer.competency_id,
                    verification_class=transfer.verification_class,
                    disposition="passed",
                    independence="independent",
                    assistance="none",
                    reasoning="verified",
                    evaluator_id="g06-probe-worker",
                    evaluator_version="v1",
                    confidence=95,
                ),
            ),
        )
    )

    assert result.version == 5
    assert repository.commits[-1].event_type == "learner.probe.evaluated"
    qualification = next(
        item for item in result.plan.qualifications if item.competency_id == evidence.competency_id
    )
    assert qualification.satisfied_classes == ["independent", "transfer"]
