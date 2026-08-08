from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.provenance import (
    InvalidCheckpointChainError,
    WorkChallengeBindingError,
    WorkProvenanceAlreadyEvaluatedError,
    WorkProvenanceError,
)
from ai_learning_platform_api.learning.schemas import (
    ArtifactCheckpointView,
    EvidenceRecordView,
    PlanRequest,
    PlanView,
    ProgressRequest,
    TrustedEvidenceVerdict,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceState,
    WorkProvenanceSubmission,
)

_SECRET = "g07-work-provenance-secret-with-more-than-thirty-two-bytes"
_START = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


def _service(clock: MutableClock) -> LearningPlanService:
    return LearningPlanService(
        _SECRET,
        clock=clock,
        id_factory=lambda: UUID("77777777-7777-4777-8777-777777777777"),
    )


def _record_work(service: LearningPlanService) -> tuple[PlanView, EvidenceRecordView]:
    plan = service.create_plan(PlanRequest(learner_name="Provenance Learner", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection=(
                "I implemented the task independently, documented trade-offs, and verified the "
                "learner-specific acceptance contract with repeatable checks."
            ),
            evidence_reference="repo://g07/work",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = progressed.evidence_history[-1]
    assert evidence.source_high_stakes_eligible is True
    return progressed, evidence


def _work_record(plan: PlanView, evidence_id: str) -> WorkProvenanceState:
    return next(item for item in plan.work_provenance if item.evidence_id == evidence_id)


def _checkpoints(*, answer_level: bool = False) -> list[ArtifactCheckpointView]:
    return [
        ArtifactCheckpointView(
            checkpoint_id="checkpoint-01",
            artifact_sha256="a" * 64,
            parent_checkpoint_id="",
            created_at=_START.isoformat(),
            change_summary="Initial independently authored implementation and tests.",
            toolchain=["python", "pytest"],
            assistance="answer_level" if answer_level else "none",
        ),
        ArtifactCheckpointView(
            checkpoint_id="checkpoint-02",
            artifact_sha256="b" * 64,
            parent_checkpoint_id="checkpoint-01",
            created_at=(_START + timedelta(hours=1)).isoformat(),
            change_summary="Applied hidden modification and repaired the seeded defect.",
            toolchain=["python", "pytest", "git"],
            assistance="none",
        ),
    ]


def _submission(
    challenge_plan: PlanView,
    evidence: EvidenceRecordView,
    *,
    answer_level: bool = False,
    source_attribution: str = "Self-authored; standard-library and project docs consulted.",
) -> WorkProvenanceSubmission:
    record = _work_record(challenge_plan, evidence.evidence_id)
    by_kind = {item.kind: item.challenge_id for item in record.challenges}
    return WorkProvenanceSubmission(
        evidence_id=evidence.evidence_id,
        artifact_id="artifact-g07-001",
        final_artifact_sha256="b" * 64,
        checkpoints=_checkpoints(answer_level=answer_level),
        assistance_disclosure="answer_level" if answer_level else "none",
        source_attribution=source_attribution,
        modification_challenge_id=by_kind["modification"],
        modification_evidence_reference="repo://g07/modification-diff",
        debugging_challenge_id=by_kind["debugging"],
        debugging_evidence_reference="repo://g07/debugging-trace",
        defense_challenge_id=by_kind["defense"],
        defense_response=(
            "I chose the smaller boundary because it preserves deterministic ownership. The main "
            "trade-off is additional explicit state, but it prevents provider output from becoming "
            "authority. I rejected a shared mutable cache because replay and isolation "
            "would weaken."
        ),
    )


def _work_verdict(
    evidence: EvidenceRecordView,
    *,
    authorship: bool = True,
    modification: bool = True,
    debugging: bool = True,
    defense: bool = True,
) -> TrustedWorkProvenanceVerdict:
    return TrustedWorkProvenanceVerdict(
        evidence_id=evidence.evidence_id,
        artifact_id="artifact-g07-001",
        disposition="accepted",
        authorship_verified=authorship,
        modification_verified=modification,
        debugging_verified=debugging,
        defense_verified=defense,
        evaluator_id="trusted-g07-work-reviewer",
        evaluator_version="g07-v1",
        confidence=97,
        findings=[],
    )


def _evidence_verdict(evidence: EvidenceRecordView) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="trusted-g07-evidence-reviewer",
        evaluator_version="g07-v1",
        rubric_version=evidence.source_rubric_version,
        instance_contract_hash=evidence.source_instance_contract_hash,
        confidence=96,
    )


def _verified_work(
    service: LearningPlanService,
    progressed: PlanView,
    evidence: EvidenceRecordView,
) -> PlanView:
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    return service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_work_verdict(evidence),
    )


def test_polished_artifact_alone_cannot_enter_high_stakes_qualification() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)

    with pytest.raises(WorkProvenanceError):
        service.evaluate_evidence(
            state_token=progressed.state_token,
            verdict=_evidence_verdict(evidence),
        )


def test_verified_checkpoint_modification_debugging_and_defense_unlock_evidence() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    verified = _verified_work(service, progressed, evidence)

    provenance = _work_record(verified, evidence.evidence_id)
    assert provenance.status == "verified"
    assert provenance.eligible_for_readiness is True
    assert provenance.issues == []

    evaluated = service.evaluate_evidence(
        state_token=verified.state_token,
        verdict=_evidence_verdict(evidence),
    )
    qualification = next(
        item for item in evaluated.qualifications if item.competency_id == evidence.competency_id
    )
    assert "independent" in qualification.satisfied_classes


def test_answer_level_assistance_blocks_work_even_when_evaluator_accepts() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence, answer_level=True),
    )
    evaluated_work = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_work_verdict(evidence),
    )
    provenance = _work_record(evaluated_work, evidence.evidence_id)
    assert provenance.eligible_for_readiness is False
    assert "answer_level_assistance" in provenance.issues

    with pytest.raises(WorkProvenanceError):
        service.evaluate_evidence(
            state_token=evaluated_work.state_token,
            verdict=_evidence_verdict(evidence),
        )


def test_broken_checkpoint_parent_chain_fails_closed() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submission = _submission(issued, evidence)
    broken = submission.model_copy(
        update={
            "checkpoints": [
                submission.checkpoints[0],
                submission.checkpoints[1].model_copy(
                    update={"parent_checkpoint_id": "wrong-parent"}
                ),
            ]
        }
    )

    with pytest.raises(InvalidCheckpointChainError):
        service.submit_work_provenance(
            state_token=issued.state_token,
            submission=broken,
        )


def test_challenge_identity_is_bound_to_the_post_artifact_verification() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submission = _submission(issued, evidence).model_copy(
        update={"debugging_challenge_id": "work-debugging-forged"}
    )

    with pytest.raises(WorkChallengeBindingError):
        service.submit_work_provenance(
            state_token=issued.state_token,
            submission=submission,
        )


def test_copied_or_unverified_authorship_never_becomes_readiness_eligible() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(
            issued,
            evidence,
            source_attribution="Imported sample implementation; authorship requires review.",
        ),
    )
    evaluated = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=_work_verdict(evidence, authorship=False),
    )
    provenance = _work_record(evaluated, evidence.evidence_id)
    assert provenance.eligible_for_readiness is False
    assert "authorship_unverified" in provenance.issues


def test_exact_duplicate_work_verdict_is_idempotent_but_conflicting_verdict_is_rejected() -> None:
    service = _service(MutableClock(_START))
    progressed, evidence = _record_work(service)
    issued = service.issue_work_verification(
        state_token=progressed.state_token,
        evidence_id=evidence.evidence_id,
    )
    submitted = service.submit_work_provenance(
        state_token=issued.state_token,
        submission=_submission(issued, evidence),
    )
    verdict = _work_verdict(evidence)
    first = service.evaluate_work_provenance(
        state_token=submitted.state_token,
        verdict=verdict,
    )
    duplicate = service.evaluate_work_provenance(
        state_token=first.state_token,
        verdict=verdict,
    )
    assert duplicate.sequence == first.sequence

    with pytest.raises(WorkProvenanceAlreadyEvaluatedError):
        service.evaluate_work_provenance(
            state_token=first.state_token,
            verdict=verdict.model_copy(update={"defense_verified": False}),
        )
