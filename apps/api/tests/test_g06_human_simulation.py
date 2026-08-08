from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.schemas import (
    PlanRequest,
    ProgressRequest,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
)

_SECRET = "g06-human-simulation-secret-with-more-than-thirty-two-bytes"
_START = datetime(2026, 8, 8, 9, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.value = _START

    def __call__(self) -> datetime:
        return self.value

    def advance(self, *, days: int) -> None:
        self.value += timedelta(days=days)


def _service(clock: Clock) -> LearningPlanService:
    return LearningPlanService(
        _SECRET,
        clock=clock,
        id_factory=lambda: UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    )


def _record(service: LearningPlanService):
    plan = service.create_plan(PlanRequest(learner_name="Human Simulation", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    completed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="I completed the exact task and documented verification evidence.",
            evidence_reference="repo://g06-human",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    return completed, completed.evidence_history[-1]


def _evidence(evidence, *, assisted: bool = False) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="assisted" if assisted else "independent",
        assistance="hint" if assisted else "none",
        reasoning="verified",
        evaluator_id="g06-human-evaluator",
        evaluator_version="v1",
        rubric_version=evidence.source_rubric_version,
        instance_contract_hash=evidence.source_instance_contract_hash,
        confidence=95,
    )


def _probe(plan, proof_class: str):
    return next(item for item in plan.verification_probes if item.verification_class == proof_class)


def _pass(probe) -> TrustedProbeVerdict:
    return TrustedProbeVerdict(
        probe_id=probe.probe_id,
        competency_id=probe.competency_id,
        verification_class=probe.verification_class,
        disposition="passed",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="g06-human-probe",
        evaluator_version="v1",
        confidence=94,
    )


def _qualification(plan, competency_id: str):
    return next(item for item in plan.qualifications if item.competency_id == competency_id)


def test_assisted_learner_cannot_turn_hint_success_into_delayed_independent_proof() -> None:
    clock = Clock()
    service = _service(clock)
    completed, evidence = _record(service)
    evaluated = service.evaluate_evidence(
        state_token=completed.state_token,
        verdict=_evidence(evidence, assisted=True),
    )
    clock.advance(days=45)
    resumed = service.resume(evaluated.state_token)
    qualification = _qualification(resumed, evidence.competency_id)

    assert qualification.assisted_evidence_ids == [evidence.evidence_id]
    assert qualification.independent_evidence_ids == []
    assert qualification.satisfied_classes == []
    assert qualification.scheduled_probe_ids == []
    assert qualification.fully_qualified is False


def test_fast_learner_still_waits_for_real_7d_and_30d_no_hint_proof() -> None:
    clock = Clock()
    service = _service(clock)
    completed, evidence = _record(service)
    current = service.evaluate_evidence(
        state_token=completed.state_token,
        verdict=_evidence(evidence),
    )
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_pass(_probe(current, "transfer")),
    )
    qualification = _qualification(current, evidence.competency_id)
    assert qualification.satisfied_classes == ["independent", "transfer"]
    assert qualification.fully_qualified is False

    clock.advance(days=7)
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_pass(_probe(current, "retention_7d")),
    )
    assert _qualification(current, evidence.competency_id).fully_qualified is False

    clock.advance(days=23)
    current = service.evaluate_probe(
        state_token=current.state_token,
        verdict=_pass(_probe(current, "retention_30d")),
    )
    assert _qualification(current, evidence.competency_id).fully_qualified is True


def test_struggling_learner_failed_transfer_remains_reopened() -> None:
    clock = Clock()
    service = _service(clock)
    completed, evidence = _record(service)
    current = service.evaluate_evidence(
        state_token=completed.state_token,
        verdict=_evidence(evidence),
    )
    transfer = _probe(current, "transfer")
    failed = _pass(transfer).model_copy(update={"disposition": "failed"})
    current = service.evaluate_probe(state_token=current.state_token, verdict=failed)
    qualification = _qualification(current, evidence.competency_id)

    assert "transfer" in qualification.failed_classes
    assert "transfer" in qualification.missing_classes
    assert qualification.fully_qualified is False


def test_delayed_returning_learner_resumes_same_due_obligations_deterministically() -> None:
    clock = Clock()
    service = _service(clock)
    completed, evidence = _record(service)
    current = service.evaluate_evidence(
        state_token=completed.state_token,
        verdict=_evidence(evidence),
    )
    original_probes = list(current.verification_probes)

    clock.advance(days=31)
    resumed = service.resume(current.state_token)
    qualification = _qualification(resumed, evidence.competency_id)

    assert resumed.verification_probes == original_probes
    assert qualification.fully_qualified is False
    assert set(qualification.scheduled_probe_ids) == {item.probe_id for item in original_probes}
    assert len(resumed.state_token) < 65_536
