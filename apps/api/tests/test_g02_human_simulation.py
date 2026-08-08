from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.schemas import (
    AssessmentAnswer,
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    CompetencyRating,
    PlanRequest,
    PlanView,
    ProgressRequest,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanService

SECRET = "g02-human-simulation-secret-with-at-least-thirty-two-bytes"
NOW = datetime(2026, 8, 8, 5, 0, tzinfo=UTC)


def _service() -> LearningPlanService:
    return LearningPlanService(
        SECRET,
        clock=lambda: NOW,
        id_factory=lambda: UUID("33333333-3333-4333-8333-333333333333"),
    )


def _complete_current_activity(service: LearningPlanService, plan: PlanView) -> PlanView:
    assert plan.current_activity is not None
    return service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=plan.current_activity.id,
            reflection=(
                "I completed the work and can describe my choices, but this statement is only my "
                "own account of what happened."
            ),
            criteria_met=list(plan.current_activity.acceptance_criteria),
            confidence=4,
        )
    )


def _verdict(
    *,
    evidence_id: str,
    competency_id: str,
    disposition: str = "accepted",
    independence: str = "unverified",
    assistance: str = "unknown",
    reasoning: str = "not_observed",
) -> TrustedEvidenceVerdict:
    return TrustedEvidenceVerdict.model_validate(
        {
            "evidence_id": evidence_id,
            "competency_id": competency_id,
            "disposition": disposition,
            "independence": independence,
            "assistance": assistance,
            "reasoning": reasoning,
            "evaluator_id": "human-simulation-rubric",
            "evaluator_version": "g02-sim-v1",
            "rubric_version": "g02-sim-rubric-v1",
            "confidence": 95,
            "findings": ["Observed behavior was evaluated against the deterministic rubric."],
            "misconception_codes": [],
        }
    )


def _competency_status(plan: PlanView, competency_id: str) -> str:
    return next(
        item.status for item in plan.competency_evidence if item.competency_id == competency_id
    )


def test_overconfident_learner_cannot_self_certify_through_rating_work_or_quiz() -> None:
    """Simulate a learner trying every public self-service path to create a mastery claim."""
    service = _service()
    created = service.create_plan(
        PlanRequest(
            learner_name="Overconfident Learner",
            ratings=[CompetencyRating(competency_id="python", score=4)],
        )
    )
    progressed = _complete_current_activity(service, created)

    assessment = service.start_assessment(
        AssessmentStartRequest(state_token=progressed.state_token, question_count=2)
    )
    submitted = service.submit_assessment(
        AssessmentSubmitRequest(
            state_token=progressed.state_token,
            attempt_token=assessment.attempt_token,
            answers=[
                AssessmentAnswer(question_id=item.id, option_id=item.options[0].id)
                for item in assessment.questions
            ],
        )
    )

    assert created.planning_signal_percent > 0
    assert progressed.evidence_history[-1].source == "learner_attested"
    assert progressed.evidence_history[-1].disposition == "recorded"
    assert submitted.plan.assessment_coverage_percent > 0
    assert submitted.plan.evidence_evaluations == []
    assert all(item.status == "unverified" for item in submitted.plan.competency_evidence)
    assert submitted.plan.claim_state == "validation_locked"
    assert submitted.plan.verified_readiness_percent is None


def test_assisted_learner_requires_later_independent_observation_before_promotion() -> None:
    """Simulate hint-assisted work followed by a genuinely independent re-observation."""
    service = _service()
    progressed = _complete_current_activity(
        service,
        service.create_plan(PlanRequest(learner_name="Assisted Learner")),
    )
    evidence = progressed.evidence_history[-1]

    assisted = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_verdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            independence="assisted",
            assistance="hint",
            reasoning="verified",
        ),
    )
    assert _competency_status(assisted, evidence.competency_id) == "partial"
    assert assisted.review_state[0].stage == "evidence_follow_up"

    independent = service.evaluate_evidence(
        state_token=assisted.state_token,
        verdict=_verdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            independence="independent",
            assistance="none",
            reasoning="verified",
        ),
    )
    assert _competency_status(independent, evidence.competency_id) == "independent"
    assert independent.review_state[0].stage == "retention_candidate"
    assert independent.verified_readiness_percent is None
    assert independent.claim_state == "validation_locked"


def test_dispute_is_visible_without_silently_erasing_prior_independent_observation() -> None:
    """Simulate a later dispute while preserving the immutable evaluation history."""
    service = _service()
    progressed = _complete_current_activity(
        service,
        service.create_plan(PlanRequest(learner_name="Disputed Evidence Learner")),
    )
    evidence = progressed.evidence_history[-1]
    accepted = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_verdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            independence="independent",
            assistance="none",
            reasoning="verified",
        ),
    )
    disputed = service.evaluate_evidence(
        state_token=accepted.state_token,
        verdict=_verdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            disposition="disputed",
        ),
    )

    state = next(
        item for item in disputed.competency_evidence if item.competency_id == evidence.competency_id
    )
    assert state.status == "independent"
    assert evidence.evidence_id in state.accepted_evidence_ids
    assert evidence.evidence_id in state.disputed_evidence_ids
    assert [item.disposition for item in disputed.evidence_evaluations] == ["accepted", "disputed"]
    assert disputed.evidence_history[-1].disposition == "disputed"
    assert disputed.verified_readiness_percent is None


def test_resume_replays_the_same_authoritative_evidence_projection() -> None:
    """Simulate a returning learner and prove resume does not manufacture state changes."""
    service = _service()
    progressed = _complete_current_activity(
        service,
        service.create_plan(PlanRequest(learner_name="Returning Learner")),
    )
    evidence = progressed.evidence_history[-1]
    evaluated = service.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=_verdict(
            evidence_id=evidence.evidence_id,
            competency_id=evidence.competency_id,
            independence="independent",
            assistance="none",
            reasoning="verified",
        ),
    )

    first_resume = service.resume(evaluated.state_token)
    second_resume = service.resume(evaluated.state_token)

    assert first_resume.model_dump() == second_resume.model_dump()
    assert first_resume.competency_evidence == evaluated.competency_evidence
    assert first_resume.evidence_evaluations == evaluated.evidence_evaluations
    assert first_resume.active_misconceptions == evaluated.active_misconceptions
    assert first_resume.claim_state == "validation_locked"
    assert first_resume.verified_readiness_percent is None
