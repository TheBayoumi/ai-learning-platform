from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.provenance import WorkProvenanceError
from ai_learning_platform_api.learning.schemas import (
    ArtifactCheckpointView,
    AssistanceLevel,
    EvidenceRecordView,
    PlanRequest,
    PlanView,
    ProgressRequest,
    TrustedEvidenceVerdict,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceSubmission,
)

_SECRET = "g07-human-simulation-secret-with-more-than-thirty-two-bytes"
_START = datetime(2026, 8, 8, 9, 0, tzinfo=UTC)


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def _service() -> LearningPlanService:
    return LearningPlanService(
        _SECRET,
        clock=MutableClock(_START),
        id_factory=lambda: UUID("70707070-7070-4707-8707-707070707070"),
    )


def _artifact(service: LearningPlanService, name: str) -> tuple[PlanView, EvidenceRecordView]:
    plan = service.create_plan(PlanRequest(learner_name=name, weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection=(
                "I recorded why I chose this implementation, what failed, and how each acceptance "
                "criterion was verified without treating completion as proof of mastery."
            ),
            evidence_reference=f"repo://g07/{name.lower().replace(' ', '-')}",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    return progressed, progressed.evidence_history[-1]


def _submission(
    issued: PlanView,
    evidence: EvidenceRecordView,
    *,
    assistance: AssistanceLevel = "none",
    defense: str | None = None,
) -> WorkProvenanceSubmission:
    record = next(
        item for item in issued.work_provenance if item.evidence_id == evidence.evidence_id
    )
    challenge_ids = {item.kind: item.challenge_id for item in record.challenges}
    return WorkProvenanceSubmission(
        evidence_id=evidence.evidence_id,
        artifact_id="simulation-artifact",
        final_artifact_sha256="d" * 64,
        checkpoints=[
            ArtifactCheckpointView(
                checkpoint_id="simulation-checkpoint-1",
                artifact_sha256="c" * 64,
                parent_checkpoint_id="",
                created_at=_START.isoformat(),
                change_summary="Initial implementation before the hidden challenge.",
                toolchain=["git", "python"],
                assistance=assistance,
            ),
            ArtifactCheckpointView(
                checkpoint_id="simulation-checkpoint-2",
                artifact_sha256="d" * 64,
                parent_checkpoint_id="simulation-checkpoint-1",
                created_at=(_START + timedelta(hours=1)).isoformat(),
                change_summary="Modification and debug correction after challenge issuance.",
                toolchain=["git", "python", "pytest"],
                assistance="none",
            ),
        ],
        assistance_disclosure=assistance,
        source_attribution="Learner-authored work; consulted project documentation.",
        modification_challenge_id=challenge_ids["modification"],
        modification_evidence_reference="repo://simulation/modification",
        debugging_challenge_id=challenge_ids["debugging"],
        debugging_evidence_reference="repo://simulation/debugging",
        defense_challenge_id=challenge_ids["defense"],
        defense_response=defense
        or (
            "The design isolates authority in deterministic state. I rejected the shortcut because "
            "it would make replay depend on provider behavior. The failure mode I tested was stale "
            "state after a conflicting update, and I corrected it at the ownership boundary."
        ),
    )


def _trusted_work(
    evidence: EvidenceRecordView,
    *,
    authorship: bool = True,
    modification: bool = True,
    debugging: bool = True,
    defense: bool = True,
) -> TrustedWorkProvenanceVerdict:
    return TrustedWorkProvenanceVerdict(
        evidence_id=evidence.evidence_id,
        artifact_id="simulation-artifact",
        disposition="accepted",
        authorship_verified=authorship,
        modification_verified=modification,
        debugging_verified=debugging,
        defense_verified=defense,
        evaluator_id="simulation-work-reviewer",
        evaluator_version="g07-sim-v1",
        confidence=95,
    )


def _trusted_evidence(evidence: EvidenceRecordView) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="simulation-evidence-reviewer",
        evaluator_version="g07-sim-v1",
        rubric_version=evidence.source_rubric_version,
        instance_contract_hash=evidence.source_instance_contract_hash,
        confidence=95,
    )


def _run_work_review(
    service: LearningPlanService,
    progressed: PlanView,
    evidence: EvidenceRecordView,
    *,
    submission: WorkProvenanceSubmission | None = None,
    verdict: TrustedWorkProvenanceVerdict | None = None,
) -> PlanView:
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=submission or _submission(issued, evidence),
    )
    return service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=verdict or _trusted_work(evidence),
    )


def test_copied_artifact_learner_cannot_turn_polish_into_authoritative_evidence() -> None:
    service = _service()
    progressed, evidence = _artifact(service, "Copied Artifact Learner")
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    reviewed = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_trusted_work(evidence, authorship=False),
    )
    assert reviewed.work_provenance[-1].eligible_for_readiness is False

    with pytest.raises(WorkProvenanceError):
        service.evaluate_evidence(
            state_token=reviewed.state_token,
            verdict=_trusted_evidence(evidence),
        )


def test_modified_artifact_learner_must_prove_the_hidden_change() -> None:
    service = _service()
    progressed, evidence = _artifact(service, "Modified Artifact Learner")
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    reviewed = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_trusted_work(evidence, modification=False),
    )
    assert "modification_unverified" in reviewed.work_provenance[-1].issues
    assert reviewed.work_provenance[-1].eligible_for_readiness is False


def test_debugging_learner_only_unlocks_work_after_independent_debug_proof() -> None:
    service = _service()
    progressed, evidence = _artifact(service, "Debugging Learner")
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    reviewed = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_trusted_work(evidence, debugging=True),
    )
    assert reviewed.work_provenance[-1].debugging_verified is True
    assert reviewed.work_provenance[-1].eligible_for_readiness is True


def test_defense_recovery_learner_remains_blocked_when_defense_is_not_verified() -> None:
    service = _service()
    progressed, evidence = _artifact(service, "Defense Recovery Learner")
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    reviewed = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_trusted_work(evidence, defense=False),
    )
    assert "defense_unverified" in reviewed.work_provenance[-1].issues
    assert reviewed.work_provenance[-1].eligible_for_readiness is False


def test_verified_work_and_defense_can_then_enter_the_g06_independent_path() -> None:
    service = _service()
    progressed, evidence = _artifact(service, "Verified Work Learner")
    reviewed = _run_work_review(service, progressed, evidence)
    evaluated = service.evaluate_evidence(
        state_token=reviewed.state_token,
        verdict=_trusted_evidence(evidence),
    )
    qualification = next(
        item for item in evaluated.qualifications if item.competency_id == evidence.competency_id
    )
    assert "independent" in qualification.satisfied_classes
    assert reviewed.work_provenance[-1].eligible_for_readiness is True
