from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.catalog import ROLE_CATALOG
from ai_learning_platform_api.learning.planner import target_fingerprint
from ai_learning_platform_api.learning.role_profile import profile_for
from ai_learning_platform_api.learning.schemas import (
    CompetencyRating,
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec

SECRET = "g03-curriculum-planner-secret-with-at-least-thirty-two-bytes"
NOW = datetime(2026, 8, 8, 6, 0, tzinfo=UTC)


def _service() -> LearningPlanService:
    return LearningPlanService(
        SECRET,
        clock=lambda: NOW,
        id_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
    )


def _complete_competency(
    service: LearningPlanService,
    state_token: str,
    competency_id: str,
) -> tuple[str, str]:
    plan = service.resume(state_token)
    activity = next(
        item
        for item in plan.active_plan_version.activities
        if item.kind == "build" and item.competency_id == competency_id
    )
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection=(
                "I completed the bounded deliverable and can explain the decisions and trade-offs "
                "that should be checked independently."
            ),
            criteria_met=list(activity.acceptance_criteria),
            confidence=3,
        )
    )
    return progressed.state_token, progressed.evidence_history[-1].evidence_id


def _verdict(
    evidence_id: str,
    competency_id: str,
    *,
    independence: str = "independent",
    assistance: str = "none",
    reasoning: str = "verified",
    disposition: str = "accepted",
    misconceptions: list[str] | None = None,
) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict.model_validate(
        {
            "evidence_id": evidence_id,
            "competency_id": competency_id,
            "disposition": disposition,
            "independence": independence,
            "assistance": assistance,
            "reasoning": reasoning,
            "evaluator_id": "g03-deterministic-evaluator",
            "evaluator_version": "1",
            "rubric_version": "role-rubric-v1",
            "confidence": 96,
            "findings": ["Observed behavior satisfies the evaluated criterion."],
            "misconception_codes": misconceptions or [],
        }
    )


def test_every_role_profile_graph_is_complete_and_closed() -> None:
    for role in ROLE_CATALOG.values():
        graph = profile_for(role)
        role_ids = {item.identifier for item in role.competencies}

        assert graph.role_id == role.identifier
        assert graph.role_version == role.version
        assert set(graph.competencies) == role_ids
        assert graph.graph_version.startswith(role.version)
        assert graph.evidence_policy_version
        for competency in graph.competencies.values():
            assert set(competency.prerequisites) <= role_ids
            assert competency.competency_id not in competency.prerequisites
            assert "independent" in competency.evidence_requirements
            assert "no_assistance" in competency.evidence_requirements
            assert "reasoning_verified" in competency.evidence_requirements


def test_initial_plan_is_immutable_version_bound_to_exact_target_and_profile() -> None:
    service = _service()
    plan = service.create_plan(
        PlanRequest(
            learner_name="Versioned Learner",
            weekly_hours=8,
            experience_summary="Embedded engineer moving into backend systems.",
        )
    )
    version = plan.active_plan_version

    assert version.revision == 0
    assert version.trigger == "initial"
    assert version.role_id == plan.role.id
    assert version.role_version == plan.role.version
    assert version.graph_version == plan.role.graph_version
    assert version.evidence_policy_version == plan.role.evidence_policy_version
    assert version.target_fingerprint == target_fingerprint(plan.target)
    assert version.activities
    assert version.delta.previous_plan_version_id is None
    assert version.delta.added_activity_ids == [item.id for item in version.activities]
    assert plan.plan_history == [version]
    assert plan.claim_state == "validation_locked"
    assert plan.verified_readiness_percent is None


def test_self_report_cannot_bypass_prerequisites_or_authoritative_evidence() -> None:
    service = _service()
    plan = service.create_plan(
        PlanRequest(
            learner_name="Overconfident FastAPI Learner",
            weekly_hours=20,
            ratings=[CompetencyRating(competency_id="fastapi", score=4)],
        )
    )
    fastapi = next(
        item for item in plan.active_plan_version.priorities if item.competency_id == "fastapi"
    )

    assert fastapi.evidence_status == "unverified"
    assert set(fastapi.blocked_by) == {"python", "rest"}
    assert fastapi.diagnostic_signal_percent == 100
    assert fastapi.authoritative_gap_percent == 100
    assert all(
        item.competency_id != "fastapi"
        for item in plan.active_plan_version.activities
        if item.kind == "build"
    )
    assert "cannot satisfy evidence" in fastapi.reason


def test_trusted_independent_prerequisites_unlock_downstream_work_and_create_deltas() -> None:
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Fast Learner", weekly_hours=20)
    )

    token, python_evidence = _complete_competency(service, created.state_token, "python")
    after_python = service.evaluate_evidence(
        state_token=token,
        verdict=_verdict(python_evidence, "python"),
    )
    assert after_python.active_plan_version.trigger == "trusted_evidence"
    assert after_python.active_plan_version.revision == 1
    fastapi_after_python = next(
        item
        for item in after_python.active_plan_version.priorities
        if item.competency_id == "fastapi"
    )
    assert fastapi_after_python.blocked_by == ["rest"]

    token, rest_evidence = _complete_competency(service, after_python.state_token, "rest")
    after_rest = service.evaluate_evidence(
        state_token=token,
        verdict=_verdict(rest_evidence, "rest"),
    )
    fastapi_after_rest = next(
        item
        for item in after_rest.active_plan_version.priorities
        if item.competency_id == "fastapi"
    )

    assert fastapi_after_rest.blocked_by == []
    assert any(
        item.competency_id == "fastapi"
        for item in after_rest.active_plan_version.activities
        if item.kind == "build"
    )
    assert all(
        item.competency_id not in {"python", "rest"}
        for item in after_rest.active_plan_version.activities
        if item.kind == "build"
    )
    assert after_rest.active_plan_version.delta.previous_plan_version_id is not None
    assert after_rest.active_plan_version.delta.reason.startswith("trusted_evidence:")
    assert after_rest.plan_revision == 2


def test_assisted_evidence_remains_partial_and_does_not_unlock_dependents() -> None:
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Assisted Learner", weekly_hours=20)
    )
    token, evidence_id = _complete_competency(service, created.state_token, "python")
    assisted = service.evaluate_evidence(
        state_token=token,
        verdict=_verdict(
            evidence_id,
            "python",
            independence="assisted",
            assistance="hint",
        ),
    )

    python = next(
        item for item in assisted.active_plan_version.priorities if item.competency_id == "python"
    )
    fastapi = next(
        item for item in assisted.active_plan_version.priorities if item.competency_id == "fastapi"
    )

    assert python.evidence_status == "partial"
    assert python.authoritative_gap_percent > 0
    assert "python" in fastapi.blocked_by
    assert any(
        item.competency_id == "python"
        for item in assisted.active_plan_version.activities
        if item.kind == "build"
    )


def test_active_misconception_is_a_deterministic_priority_input() -> None:
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Struggling Learner", weekly_hours=20)
    )
    token, evidence_id = _complete_competency(service, created.state_token, "python")
    rejected = service.evaluate_evidence(
        state_token=token,
        verdict=_verdict(
            evidence_id,
            "python",
            disposition="rejected",
            independence="unverified",
            assistance="unknown",
            reasoning="not_observed",
            misconceptions=["boundary-condition-omission"],
        ),
    )
    python = next(
        item for item in rejected.active_plan_version.priorities if item.competency_id == "python"
    )

    assert python.evidence_status == "unverified"
    assert python.active_misconception_codes == ["boundary-condition-omission"]
    assert "active misconceptions=boundary-condition-omission" in python.reason
    assert rejected.active_plan_version.trigger == "trusted_evidence"


def test_capacity_and_focus_create_new_versions_without_changing_evidence() -> None:
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Capacity Learner", weekly_hours=8)
    )
    replanned = service.replan(
        ReplanRequest(
            state_token=created.state_token,
            weekly_hours=2,
            focus_competency_ids=["git"],
        )
    )

    builds = [item for item in replanned.active_plan_version.activities if item.kind == "build"]
    assert len(builds) <= 1
    assert replanned.active_plan_version.trigger == "manual_replan"
    assert replanned.active_plan_version.weekly_hours == 2
    assert replanned.active_plan_version.focus_competency_ids == ["git"]
    assert replanned.plan_revision == created.plan_revision + 1
    assert replanned.competency_evidence == created.competency_evidence
    assert replanned.verified_readiness_percent is None


def test_plan_history_is_bounded_and_replay_is_deterministic() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Returning Learner"))
    for index in range(8):
        plan = service.replan(
            ReplanRequest(
                state_token=plan.state_token,
                weekly_hours=4 + index,
                focus_competency_ids=[],
            )
        )

    first = service.resume(plan.state_token)
    second = service.resume(plan.state_token)

    assert len(first.plan_history) == 6
    assert first.active_plan_version.plan_version_id == first.plan_history[-1].plan_version_id
    assert first.model_dump() == second.model_dump()


def test_schema_five_state_migrates_to_plan_version_without_inventing_evidence() -> None:
    service = _service()
    codec = SignedStateCodec(SECRET)
    created = service.create_plan(PlanRequest(learner_name="Legacy Planner Learner"))
    state = codec.decode(created.state_token)
    legacy = state.model_copy(
        update={
            "schema_version": 5,
            "active_plan_version_id": None,
            "plan_versions": [],
        }
    )

    migrated = service.resume(codec.encode(legacy))
    migrated_state = codec.decode(migrated.state_token)

    assert migrated_state.schema_version == 6
    assert migrated.active_plan_version.trigger == "state_migration"
    assert migrated.active_plan_version.activities == state.activities
    assert migrated.evidence_evaluations == created.evidence_evaluations
    assert all(item.status == "unverified" for item in migrated.competency_evidence)
    assert migrated.verified_readiness_percent is None
