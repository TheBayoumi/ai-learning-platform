from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.schemas import (
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanService

SECRET = "g03-human-simulation-secret-with-at-least-thirty-two-bytes"
NOW = datetime(2026, 8, 8, 6, 15, tzinfo=UTC)


def _service() -> LearningPlanService:
    return LearningPlanService(
        SECRET,
        clock=lambda: NOW,
        id_factory=lambda: UUID("55555555-5555-4555-8555-555555555555"),
    )


def _submit(service: LearningPlanService, state_token: str, competency_id: str) -> tuple[str, str]:
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
                "I completed this work and can defend the decisions, but I understand my own "
                "submission is not independent evidence."
            ),
            criteria_met=list(activity.acceptance_criteria),
            confidence=3,
        )
    )
    return progressed.state_token, progressed.evidence_history[-1].evidence_id


def _judge(
    evidence_id: str,
    competency_id: str,
    *,
    disposition: str = "accepted",
    independence: str = "independent",
    assistance: str = "none",
    reasoning: str = "verified",
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
            "evaluator_id": "g03-human-simulator",
            "evaluator_version": "1",
            "rubric_version": "g03-human-rubric-v1",
            "confidence": 95,
            "findings": ["Simulated independent observation completed."],
            "misconception_codes": misconceptions or [],
        }
    )


def test_struggling_learner_gets_remediation_not_false_progress() -> None:
    """A failed observed task keeps the gap open and feeds the misconception into replanning."""
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Struggling Learner", weekly_hours=20)
    )
    token, evidence_id = _submit(service, created.state_token, "python")
    judged = service.evaluate_evidence(
        state_token=token,
        verdict=_judge(
            evidence_id,
            "python",
            disposition="rejected",
            independence="unverified",
            assistance="unknown",
            reasoning="not_observed",
            misconceptions=["state-mutation-confusion"],
        ),
    )

    python = next(item for item in judged.competency_evidence if item.competency_id == "python")
    priority = next(
        item for item in judged.active_plan_version.priorities if item.competency_id == "python"
    )
    assert python.status == "unverified"
    assert priority.active_misconception_codes == ["state-mutation-confusion"]
    assert any(
        item.competency_id == "python"
        for item in judged.active_plan_version.activities
        if item.kind == "build"
    )
    assert judged.verified_readiness_percent is None


def test_fast_learner_unlocks_dependencies_without_repeating_independent_roots() -> None:
    """Strong evidence compresses redundant work while preserving the dependency graph."""
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Fast Learner", weekly_hours=20))
    for competency_id in ("python", "rest"):
        token, evidence_id = _submit(service, plan.state_token, competency_id)
        plan = service.evaluate_evidence(
            state_token=token,
            verdict=_judge(evidence_id, competency_id),
        )

    build_ids = {
        item.competency_id
        for item in plan.active_plan_version.activities
        if item.kind == "build"
    }
    fastapi = next(
        item for item in plan.active_plan_version.priorities if item.competency_id == "fastapi"
    )
    assert "python" not in build_ids
    assert "rest" not in build_ids
    assert "fastapi" in build_ids
    assert fastapi.blocked_by == []
    assert plan.plan_revision == 2


def test_assisted_learner_cannot_unlock_downstream_curriculum() -> None:
    """Hint-assisted success stays partial and the downstream prerequisite remains closed."""
    service = _service()
    created = service.create_plan(
        PlanRequest(learner_name="Assisted Learner", weekly_hours=20)
    )
    token, evidence_id = _submit(service, created.state_token, "python")
    assisted = service.evaluate_evidence(
        state_token=token,
        verdict=_judge(
            evidence_id,
            "python",
            independence="assisted",
            assistance="hint",
        ),
    )

    fastapi = next(
        item for item in assisted.active_plan_version.priorities if item.competency_id == "fastapi"
    )
    assert "python" in fastapi.blocked_by
    assert any(
        item.competency_id == "python"
        for item in assisted.active_plan_version.activities
        if item.kind == "build"
    )
    assert assisted.claim_state == "validation_locked"


def test_returning_learner_replays_exact_plan_then_capacity_change_creates_a_delta() -> None:
    """Resume is stable; a real constraint change creates a new immutable version instead."""
    service = _service()
    created = service.create_plan(PlanRequest(learner_name="Returning Learner", weekly_hours=8))
    resumed = service.resume(created.state_token)
    resumed_again = service.resume(created.state_token)

    assert resumed.active_plan_version == created.active_plan_version
    assert resumed.model_dump() == resumed_again.model_dump()

    replanned = service.replan(
        ReplanRequest(
            state_token=resumed.state_token,
            weekly_hours=4,
            focus_competency_ids=["git"],
        )
    )
    assert replanned.active_plan_version.plan_version_id != resumed.active_plan_version.plan_version_id
    assert (
        replanned.active_plan_version.delta.previous_plan_version_id
        == resumed.active_plan_version.plan_version_id
    )
    assert replanned.active_plan_version.trigger == "manual_replan"
    assert replanned.plan_history[-2].plan_version_id == resumed.active_plan_version.plan_version_id
