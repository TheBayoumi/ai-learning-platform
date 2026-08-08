from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.qualification import (
    ProbeAlreadyEvaluatedError,
    ProbeBindingMismatchError,
    ProbeNotDueError,
    UnknownProbeError,
)
from ai_learning_platform_api.learning.schemas import (
    CompetencyQualificationView,
    EvidenceRecordView,
    PlanRequest,
    PlanView,
    ProgressRequest,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
    VerificationClass,
    VerificationProbeView,
)

_SECRET = "g06-retention-transfer-secret-with-more-than-thirty-two-bytes"
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
        id_factory=lambda: UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    )


def _recorded(service: LearningPlanService) -> tuple[PlanView, EvidenceRecordView]:
    plan = service.create_plan(PlanRequest(learner_name="Qualification Learner", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Implemented and verified every exact learner-specific requirement.",
            evidence_reference="repo://g06-qualification",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = progressed.evidence_history[-1]
    return progressed, evidence


def _evidence_verdict(
    evidence: EvidenceRecordView, *, assisted: bool = False
) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="assisted" if assisted else "independent",
        assistance="hint" if assisted else "none",
        reasoning="verified",
        evaluator_id="trusted-g06-evaluator",
        evaluator_version="g06-v1",
        rubric_version=evidence.source_rubric_version,
        instance_contract_hash=evidence.source_instance_contract_hash,
        confidence=96,
    )


def _probe_verdict(probe: VerificationProbeView, *, passed: bool = True) -> TrustedProbeVerdict:
    return TrustedProbeVerdict(
        probe_id=probe.probe_id,
        competency_id=probe.competency_id,
        verification_class=probe.verification_class,
        disposition="passed" if passed else "failed",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="trusted-g06-probe-evaluator",
        evaluator_version="g06-probe-v1",
        confidence=95,
    )


def _qualification(plan: PlanView, competency_id: str) -> CompetencyQualificationView:
    return next(item for item in plan.qualifications if item.competency_id == competency_id)


def _probe(plan: PlanView, verification_class: VerificationClass) -> VerificationProbeView:
    return next(
        item for item in plan.verification_probes if item.verification_class == verification_class
    )


def test_assisted_evidence_is_recorded_but_schedules_no_independent_proof() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)

    evaluated = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence, assisted=True),
    )
    qualification = _qualification(evaluated, evidence.competency_id)

    assert qualification.satisfied_classes == []
    assert qualification.independent_evidence_ids == []
    assert qualification.assisted_evidence_ids == [evidence.evidence_id]
    assert qualification.fully_qualified is False
    assert not [
        item
        for item in evaluated.verification_probes
        if item.competency_id == evidence.competency_id
    ]


def test_independent_evidence_schedules_distinct_transfer_7d_and_30d_obligations() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)

    evaluated = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence),
    )
    qualification = _qualification(evaluated, evidence.competency_id)
    probes = [
        item
        for item in evaluated.verification_probes
        if item.competency_id == evidence.competency_id
    ]

    assert qualification.satisfied_classes == ["independent"]
    assert qualification.missing_classes == ["retention_7d", "retention_30d", "transfer"]
    assert qualification.fully_qualified is False
    assert {item.verification_class for item in probes} == {
        "transfer",
        "retention_7d",
        "retention_30d",
    }
    transfer = _probe(evaluated, "transfer")
    seven = _probe(evaluated, "retention_7d")
    thirty = _probe(evaluated, "retention_30d")
    assert transfer.due_at == _START.isoformat()
    assert seven.due_at == (_START + timedelta(days=7)).isoformat()
    assert thirty.due_at == (_START + timedelta(days=30)).isoformat()
    assert transfer.unseen_instance_fingerprint.startswith("transfer-")
    assert seven.unseen_instance_fingerprint == ""
    assert thirty.unseen_instance_fingerprint == ""


def test_delayed_probe_fails_closed_before_server_owned_due_time() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)
    evaluated = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence),
    )
    seven = _probe(evaluated, "retention_7d")

    with pytest.raises(ProbeNotDueError):
        service.evaluate_probe(
            state_token=evaluated.state_token,
            verdict=_probe_verdict(seven),
        )


def test_exact_probe_binding_rejects_unknown_and_mismatched_verdicts() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)
    evaluated = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence),
    )
    transfer = _probe(evaluated, "transfer")

    unknown = _probe_verdict(transfer).model_copy(update={"probe_id": "probe-does-not-exist"})
    with pytest.raises(UnknownProbeError):
        service.evaluate_probe(state_token=evaluated.state_token, verdict=unknown)

    mismatched = _probe_verdict(transfer).model_copy(update={"verification_class": "retention_7d"})
    with pytest.raises(ProbeBindingMismatchError):
        service.evaluate_probe(state_token=evaluated.state_token, verdict=mismatched)


def test_full_independent_transfer_and_delayed_retention_proof_becomes_fully_qualified() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)
    current = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence),
    )

    transfer = _probe(current, "transfer")
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_probe_verdict(transfer),
    )
    assert _qualification(current, evidence.competency_id).satisfied_classes == [
        "independent",
        "transfer",
    ]

    clock.advance(days=7)
    seven = _probe(current, "retention_7d")
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_probe_verdict(seven),
    )
    assert _qualification(current, evidence.competency_id).fully_qualified is False

    clock.advance(days=23)
    thirty = _probe(current, "retention_30d")
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_probe_verdict(thirty),
    )
    qualification = _qualification(current, evidence.competency_id)
    assert qualification.satisfied_classes == [
        "independent",
        "retention_7d",
        "retention_30d",
        "transfer",
    ]
    assert qualification.missing_classes == []
    assert qualification.fully_qualified is True


def test_failed_probe_reopens_class_and_conflicting_rewrite_is_rejected() -> None:
    clock = MutableClock(_START)
    service = _service(clock)
    progressed, evidence = _recorded(service)
    current = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_evidence_verdict(evidence),
    )
    transfer = _probe(current, "transfer")
    failed = _probe_verdict(transfer, passed=False)
    current = service.evaluate_probe(state_token=current.state_token, verdict=failed)
    qualification = _qualification(current, evidence.competency_id)
    assert "transfer" not in qualification.satisfied_classes
    assert qualification.failed_classes == ["transfer"]
    assert qualification.fully_qualified is False
    retry = next(
        item
        for item in current.verification_probes
        if item.verification_class == "transfer" and item.status == "scheduled"
    )
    assert retry.probe_id != transfer.probe_id

    duplicate = service.evaluate_probe(state_token=current.state_token, verdict=failed)
    assert duplicate.sequence == current.sequence
    assert duplicate.state_token == current.state_token

    with pytest.raises(ProbeAlreadyEvaluatedError):
        service.evaluate_probe(
            state_token=current.state_token,
            verdict=_probe_verdict(transfer, passed=True),
        )
