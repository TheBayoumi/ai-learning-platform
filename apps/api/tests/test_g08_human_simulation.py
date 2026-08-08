from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.readiness import project_readiness
from ai_learning_platform_api.learning.readiness_service import ReadinessLearningPlanService
from ai_learning_platform_api.learning.schemas import (
    CompetencyEvidenceState,
    CompetencyQualificationState,
    EvidenceRecordView,
    LearnerState,
    PlanRequest,
    VerificationClass,
    WorkProvenanceState,
)

_SECRET = "g08-human-simulation-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 16, 0, tzinfo=UTC)
_ROLE_ID = "junior-python-backend-engineer"
_REQUIRED: list[VerificationClass] = [
    "independent",
    "retention_7d",
    "retention_30d",
    "transfer",
]


def _state() -> tuple[LearnerState, RoleDefinition]:
    service = ReadinessLearningPlanService(
        _SECRET,
        clock=lambda: _NOW,
        id_factory=lambda: UUID("81818181-8181-4818-8818-818181818181"),
    )
    plan = service.create_plan(
        PlanRequest(
            learner_name="Readiness Simulation Learner",
            target_role=_ROLE_ID,
            weekly_hours=8,
        )
    )
    return service._codec.decode(plan.state_token), ROLE_CATALOG[_ROLE_ID]


def _prove(state: LearnerState, competency_id: str) -> LearnerState:
    evidence_id = f"sim-evidence-{competency_id}"
    evidence = EvidenceRecordView(
        evidence_id=evidence_id,
        activity_id=f"sim-activity-{competency_id}",
        competency_id=competency_id,
        competency_name=competency_id,
        title="Simulation verified work",
        submitted_at=_NOW.isoformat(),
        reflection="Independent evidence used only for deterministic readiness simulation.",
        evidence_reference=f"repo://g08-sim/{competency_id}",
        criteria_met=["criterion"],
        confidence=4,
        source="trusted_evaluator",
        disposition="accepted",
        independence="independent",
        assistance="none",
        reasoning="verified",
        planning_signal_delta=0,
        next_review_at=_NOW.isoformat(),
        source_high_stakes_eligible=True,
    )
    return state.model_copy(
        update={
            "evidence_history": [
                *[item for item in state.evidence_history if item.competency_id != competency_id],
                evidence,
            ],
            "competency_evidence": {
                **state.competency_evidence,
                competency_id: CompetencyEvidenceState(
                    competency_id=competency_id,
                    status="independent",
                    accepted_evidence_ids=[evidence_id],
                    last_evaluated_at=_NOW.isoformat(),
                    no_hint_verified=True,
                    reasoning_verified=True,
                    assistance="none",
                ),
            },
            "competency_qualification": {
                **state.competency_qualification,
                competency_id: CompetencyQualificationState(
                    competency_id=competency_id,
                    satisfied_classes=_REQUIRED,
                    independent_evidence_ids=[evidence_id],
                    last_updated_at=_NOW.isoformat(),
                ),
            },
            "work_provenance": {
                **state.work_provenance,
                evidence_id: WorkProvenanceState(
                    evidence_id=evidence_id,
                    artifact_id=f"sim-artifact-{competency_id}",
                    status="verified",
                    source_high_stakes_eligible=True,
                    authorship_verified=True,
                    modification_verified=True,
                    debugging_verified=True,
                    defense_verified=True,
                    captured_at=_NOW.isoformat(),
                    evaluated_at=_NOW.isoformat(),
                    eligible_for_readiness=True,
                ),
            },
        }
    )


def test_overconfident_learner_with_only_self_report_remains_fully_blocked() -> None:
    state, role = _state()
    state = state.model_copy(
        update={
            "planning_signal": {item.identifier: 100 for item in role.competencies},
            "assessment_scores": {item.identifier: 100 for item in role.competencies},
        }
    )
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.engineering_evidence_complete is False
    assert len(projection.mandatory_gap_ids) == len(role.competencies)
    assert projection.claim_state == "validation_locked"


def test_fast_learner_strength_in_one_area_cannot_offset_an_unproven_requirement() -> None:
    state, role = _state()
    for competency in role.competencies[:-1]:
        state = _prove(state, competency.identifier)
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.mandatory_gap_ids == [role.competencies[-1].identifier]
    assert projection.engineering_evidence_complete is False


def test_disputed_returning_learner_keeps_the_dispute_visible_and_blocking() -> None:
    state, role = _state()
    for competency in role.competencies:
        state = _prove(state, competency.identifier)
    competency_id = role.competencies[0].identifier
    evidence = state.competency_evidence[competency_id]
    state = state.model_copy(
        update={
            "competency_evidence": {
                **state.competency_evidence,
                competency_id: evidence.model_copy(
                    update={"disputed_evidence_ids": ["sim-disputed-evidence"]}
                ),
            }
        }
    )
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert "sim-disputed-evidence" in projection.disputed_evidence_ids
    assert competency_id in projection.mandatory_gap_ids


def test_fully_evidenced_learner_still_requires_external_profile_approval() -> None:
    state, role = _state()
    for competency in role.competencies:
        state = _prove(state, competency.identifier)
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.engineering_evidence_complete is True
    assert projection.claim_state == "validation_locked"
    assert projection.external_approval_required is True
    assert "role_profile_external_validation_pending" in projection.uncertainties
