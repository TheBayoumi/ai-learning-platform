from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.readiness import project_readiness
from ai_learning_platform_api.learning.readiness_service import ReadinessLearningPlanService
from ai_learning_platform_api.learning.schemas import (
    CompetencyEvidenceState,
    CompetencyQualificationState,
    CompetencyRating,
    EvidenceRecordView,
    LearnerState,
    MisconceptionRecord,
    PlanRequest,
    VerificationClass,
    WorkProvenanceState,
)

_SECRET = "g08-readiness-projection-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 15, 0, tzinfo=UTC)
_ROLE_ID = "junior-python-backend-engineer"
_REQUIRED: list[VerificationClass] = [
    "independent",
    "retention_7d",
    "retention_30d",
    "transfer",
]


def _service() -> ReadinessLearningPlanService:
    return ReadinessLearningPlanService(
        _SECRET,
        clock=lambda: _NOW,
        id_factory=lambda: UUID("80808080-8080-4808-8808-808080808080"),
    )


def _base_state() -> tuple[LearnerState, RoleDefinition]:
    service = _service()
    plan = service.create_plan(
        PlanRequest(
            learner_name="Readiness Learner",
            target_role=_ROLE_ID,
            weekly_hours=8,
            ratings=[
                CompetencyRating(competency_id=item.id, score=4)
                for item in service.list_roles()[0].competencies
            ],
        )
    )
    return service._codec.decode(plan.state_token), ROLE_CATALOG[_ROLE_ID]


def _complete_competency(state: LearnerState, competency_id: str) -> LearnerState:
    evidence_id = f"evidence-g08-{competency_id}"
    evidence = EvidenceRecordView(
        evidence_id=evidence_id,
        activity_id=f"activity-g08-{competency_id}",
        competency_id=competency_id,
        competency_name=competency_id,
        title=f"Verified {competency_id} work",
        submitted_at=_NOW.isoformat(),
        reflection="Independent reasoning and work evidence captured for readiness projection.",
        evidence_reference=f"repo://g08/{competency_id}",
        criteria_met=["trusted criterion"],
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
    evidence_history = [
        item for item in state.evidence_history if item.competency_id != competency_id
    ] + [evidence]
    competency_evidence = dict(state.competency_evidence)
    competency_evidence[competency_id] = CompetencyEvidenceState(
        competency_id=competency_id,
        status="independent",
        accepted_evidence_ids=[evidence_id],
        disputed_evidence_ids=[],
        last_evaluated_at=_NOW.isoformat(),
        no_hint_verified=True,
        reasoning_verified=True,
        assistance="none",
    )
    qualification = dict(state.competency_qualification)
    qualification[competency_id] = CompetencyQualificationState(
        competency_id=competency_id,
        satisfied_classes=list(_REQUIRED),
        failed_classes=[],
        independent_evidence_ids=[evidence_id],
        assisted_evidence_ids=[],
        last_updated_at=_NOW.isoformat(),
    )
    provenance = dict(state.work_provenance)
    provenance[evidence_id] = WorkProvenanceState(
        evidence_id=evidence_id,
        artifact_id=f"artifact-{competency_id}",
        status="verified",
        source_high_stakes_eligible=True,
        authorship_verified=True,
        modification_verified=True,
        debugging_verified=True,
        defense_verified=True,
        captured_at=_NOW.isoformat(),
        evaluated_at=_NOW.isoformat(),
        eligible_for_readiness=True,
    )
    return state.model_copy(
        update={
            "evidence_history": evidence_history,
            "competency_evidence": competency_evidence,
            "competency_qualification": qualification,
            "work_provenance": provenance,
        }
    )


def _complete_all(state: LearnerState) -> LearnerState:
    for competency in ROLE_CATALOG[_ROLE_ID].competencies:
        state = _complete_competency(state, competency.identifier)
    return state


def test_high_self_report_never_removes_mandatory_readiness_gaps() -> None:
    state, role = _base_state()
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.engineering_evidence_complete is False
    assert set(projection.mandatory_gap_ids) == {
        item.identifier for item in ROLE_CATALOG[_ROLE_ID].competencies
    }
    assert projection.claim_state == "validation_locked"
    assert projection.external_approval_required is True


def test_one_complete_competency_cannot_compensate_for_other_mandatory_gaps() -> None:
    state, role = _base_state()
    first = ROLE_CATALOG[_ROLE_ID].competencies[0].identifier
    state = _complete_competency(state, first)
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    first_view = next(item for item in projection.competencies if item.competency_id == first)
    assert first_view.engineering_complete is True
    assert first not in projection.mandatory_gap_ids
    assert projection.engineering_evidence_complete is False
    assert len(projection.mandatory_gap_ids) == len(ROLE_CATALOG[_ROLE_ID].competencies) - 1


def test_disputed_evidence_reopens_a_mandatory_blocker() -> None:
    state, role = _base_state()
    state = _complete_all(state)
    competency_id = ROLE_CATALOG[_ROLE_ID].competencies[0].identifier
    evidence_state = state.competency_evidence[competency_id]
    state = state.model_copy(
        update={
            "competency_evidence": {
                **state.competency_evidence,
                competency_id: evidence_state.model_copy(
                    update={"disputed_evidence_ids": [f"disputed-{competency_id}"]}
                ),
            }
        }
    )
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    view = next(item for item in projection.competencies if item.competency_id == competency_id)
    assert "disputed_evidence_present" in view.blocker_codes
    assert competency_id in projection.mandatory_gap_ids
    assert f"disputed-{competency_id}" in projection.disputed_evidence_ids


def test_active_misconception_reopens_a_completed_competency() -> None:
    state, role = _base_state()
    state = _complete_all(state)
    competency_id = ROLE_CATALOG[_ROLE_ID].competencies[0].identifier
    state = state.model_copy(
        update={
            "misconceptions": [
                MisconceptionRecord(
                    misconception_id="misconception-g08-active",
                    competency_id=competency_id,
                    code="unsafe-assumption",
                    status="active",
                    evidence_id=f"evidence-g08-{competency_id}",
                    observed_at=_NOW.isoformat(),
                )
            ]
        }
    )
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)
    view = next(item for item in projection.competencies if item.competency_id == competency_id)

    assert view.engineering_complete is False
    assert "active_misconception" in view.blocker_codes
    assert projection.engineering_evidence_complete is False


def test_full_engineering_evidence_does_not_unlock_external_readiness_claim() -> None:
    state, role = _base_state()
    state = _complete_all(state)
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.engineering_evidence_complete is True
    assert projection.mandatory_gap_ids == []
    assert projection.claim_state == "validation_locked"
    assert projection.external_approval_required is True
    assert projection.stale_evidence_ids == []
    assert "role_profile_external_validation_pending" in projection.uncertainties
    assert "evidence_staleness_not_computable_without_expiry_metadata" in projection.uncertainties


def test_target_profile_version_mismatch_fails_engineering_projection_closed() -> None:
    state, role = _base_state()
    state = _complete_all(state)
    assert state.target is not None
    mismatched_target = state.target.model_copy(update={"role_version": "wrong-role-version"})
    projection = project_readiness(state=state, role=role, target=mismatched_target)

    assert projection.engineering_evidence_complete is False
    assert "target_role_profile_version_mismatch" in projection.uncertainties
    assert projection.claim_state == "validation_locked"


def test_provisional_overlays_are_exposed_as_unresolved_not_hidden_in_a_score() -> None:
    state, role = _base_state()
    assert state.target is not None
    projection = project_readiness(state=state, role=role, target=state.target)

    assert projection.active_overlays
    assert projection.unresolved_overlay_deltas == projection.active_overlays
    assert "overlay_deltas_not_externally_validated" in projection.uncertainties


def test_top_level_service_projects_readiness_without_a_percentage() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Projected Learner", weekly_hours=4))

    assert plan.readiness_projection is not None
    assert plan.readiness_projection.claim_state == "validation_locked"
    assert plan.verified_readiness_percent is None
    assert plan.readiness_projection.mandatory_gap_ids
