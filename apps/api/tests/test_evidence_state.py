from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from pydantic import SecretStr

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.learning.evidence import (
    EvidenceCompetencyMismatchError,
    UnknownEvidenceError,
)
from ai_learning_platform_api.learning.schemas import (
    AssessmentAnswer,
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    CompetencyEvidenceState,
    PlanRequest,
    PlanView,
    ProgressRequest,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit, StoredLearnerState
from ai_learning_platform_api.persistence.schemas import (
    PersistentEvidenceEvaluationRequest,
    PersistentPlanCreateRequest,
    PersistentProgressRequest,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.settings import Settings

SECRET = "deterministic-evidence-state-secret-with-enough-bytes"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
NOW = datetime(2026, 8, 8, 3, 30, tzinfo=UTC)


class MemoryRepository:
    def __init__(self) -> None:
        self.values: dict[tuple[str, UUID], StoredLearnerState] = {}
        self.commits: list[LearnerStateCommit] = []
        self.idempotent: dict[tuple[str, str], StoredLearnerState] = {}

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return self.values.get((account_id, learner_id))

    async def delete_account(self, *, account_id: str) -> bool:
        identities = [identity for identity in self.values if identity[0] == account_id]
        for identity in identities:
            del self.values[identity]
        return bool(identities)

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        cached = self.idempotent.get((request.account_id, request.idempotency_key))
        if cached is not None:
            return cached
        current = self.values.get((request.account_id, request.learner_id))
        version = 0 if current is None else current.version + 1
        stored = StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=version,
            state=request.state,
            updated_at=request.occurred_at,
        )
        self.values[(request.account_id, request.learner_id)] = stored
        self.idempotent[(request.account_id, request.idempotency_key)] = stored
        self.commits.append(request)
        return stored


def service() -> LearningPlanService:
    return LearningPlanService(
        SECRET,
        clock=lambda: NOW,
        id_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
    )


def recorded_plan(core: LearningPlanService) -> tuple[PlanView, str, str]:
    created = core.create_plan(PlanRequest(learner_name="Evidence Learner"))
    assert created.current_activity is not None
    progressed = core.complete_activity(
        ProgressRequest(
            state_token=created.state_token,
            activity_id=created.current_activity.id,
            reflection=(
                "I built the bounded deliverable, recorded the decisions, and described what "
                "should be verified independently next."
            ),
            criteria_met=list(created.current_activity.acceptance_criteria),
            confidence=3,
        )
    )
    evidence = progressed.evidence_history[-1]
    return progressed, evidence.evidence_id, evidence.competency_id


def verdict(
    evidence_id: str,
    competency_id: str,
    *,
    disposition: str = "accepted",
    independence: str = "unverified",
    assistance: str = "unknown",
    reasoning: str = "not_observed",
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
            "evaluator_id": "deterministic-rubric-evaluator",
            "evaluator_version": "g02-v1",
            "rubric_version": "role-rubric-v1",
            "confidence": 92,
            "findings": ["The artifact behavior matches the evaluated criterion."],
            "misconception_codes": misconceptions or [],
        }
    )


def evidence_status(plan: PlanView, competency_id: str) -> CompetencyEvidenceState:
    states = plan.competency_evidence
    return next(item for item in states if item.competency_id == competency_id)


def test_initial_and_learner_attested_work_remain_unverified() -> None:
    core = service()
    created = core.create_plan(PlanRequest(learner_name="Evidence Learner"))

    assert created.claim_state == "validation_locked"
    assert created.verified_readiness_percent is None
    assert created.competency_evidence
    assert all(item.status == "unverified" for item in created.competency_evidence)
    assert all(item.evidence_status == "unverified" for item in created.priority_competencies)

    progressed, evidence_id, competency_id = recorded_plan(core)
    record = progressed.evidence_history[-1]
    state = evidence_status(progressed, competency_id)

    assert evidence_id.startswith("evidence-")
    assert record.source == "learner_attested"
    assert record.disposition == "recorded"
    assert record.independence == "unverified"
    assert record.assistance == "unknown"
    assert record.reasoning == "submitted"
    assert state.status == "unverified"
    assert progressed.evidence_evaluations == []
    assert progressed.claim_state == "validation_locked"
    assert progressed.verified_readiness_percent is None


def test_calibration_never_promotes_authoritative_competency_evidence() -> None:
    core = service()
    created = core.create_plan(PlanRequest(learner_name="Calibration Learner"))
    attempt = core.start_assessment(
        AssessmentStartRequest(state_token=created.state_token, question_count=2)
    )
    submitted = core.submit_assessment(
        AssessmentSubmitRequest(
            state_token=created.state_token,
            attempt_token=attempt.attempt_token,
            answers=[
                AssessmentAnswer(question_id=item.id, option_id=item.options[0].id)
                for item in attempt.questions
            ],
        )
    )

    assert submitted.plan.assessment_coverage_percent > 0
    assert all(item.status == "unverified" for item in submitted.plan.competency_evidence)
    assert submitted.plan.verified_readiness_percent is None


def test_assisted_or_unverified_accepted_evidence_is_partial_only() -> None:
    core = service()
    progressed, evidence_id, competency_id = recorded_plan(core)
    evaluated = core.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=verdict(
            evidence_id,
            competency_id,
            independence="assisted",
            assistance="hint",
            reasoning="verified",
        ),
    )
    state = evidence_status(evaluated, competency_id)

    assert state.status == "partial"
    assert state.accepted_evidence_ids == [evidence_id]
    assert state.no_hint_verified is False
    assert state.reasoning_verified is True
    assert state.assistance == "hint"
    assert evaluated.review_state[0].stage == "evidence_follow_up"
    assert evaluated.claim_state == "validation_locked"
    assert evaluated.verified_readiness_percent is None


def test_independent_no_assistance_verified_reasoning_promotes_to_independent() -> None:
    core = service()
    progressed, evidence_id, competency_id = recorded_plan(core)
    evaluated = core.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=verdict(
            evidence_id,
            competency_id,
            independence="independent",
            assistance="none",
            reasoning="verified",
            misconceptions=["boundary-condition-omission"],
        ),
    )
    state = evidence_status(evaluated, competency_id)

    assert state.status == "independent"
    assert state.no_hint_verified is True
    assert state.reasoning_verified is True
    assert state.assistance == "none"
    assert evaluated.review_state[0].stage == "retention_candidate"
    assert "not itself retention proof" in evaluated.review_state[0].reason
    assert len(evaluated.active_misconceptions) == 1
    assert evaluated.active_misconceptions[0].code == "boundary-condition-omission"
    assert evaluated.claim_state == "validation_locked"
    assert evaluated.verified_readiness_percent is None


def test_rejected_and_disputed_verdicts_do_not_promote_evidence() -> None:
    core = service()
    progressed, evidence_id, competency_id = recorded_plan(core)

    rejected = core.evaluate_evidence(
        state_token=progressed.state_token,
        verdict=verdict(
            evidence_id,
            competency_id,
            disposition="rejected",
            misconceptions=["unsupported-assumption"],
        ),
    )
    rejected_state = evidence_status(rejected, competency_id)
    assert rejected_state.status == "unverified"
    assert rejected_state.accepted_evidence_ids == []
    assert rejected.active_misconceptions[0].code == "unsupported-assumption"

    disputed = core.evaluate_evidence(
        state_token=rejected.state_token,
        verdict=verdict(evidence_id, competency_id, disposition="disputed"),
    )
    disputed_state = evidence_status(disputed, competency_id)
    assert disputed_state.status == "unverified"
    assert disputed_state.disputed_evidence_ids == [evidence_id]
    assert disputed.evidence_history[-1].disposition == "disputed"
    assert disputed.verified_readiness_percent is None


def test_exact_duplicate_trusted_verdict_is_idempotent() -> None:
    core = service()
    progressed, evidence_id, competency_id = recorded_plan(core)
    trusted = verdict(
        evidence_id,
        competency_id,
        independence="independent",
        assistance="none",
        reasoning="verified",
    )
    first = core.evaluate_evidence(state_token=progressed.state_token, verdict=trusted)
    second = core.evaluate_evidence(state_token=first.state_token, verdict=trusted)

    assert second.sequence == first.sequence
    assert second.evidence_evaluations == first.evidence_evaluations
    assert len(second.evidence_evaluations) == 1


def test_unknown_or_mismatched_evidence_fails_closed() -> None:
    core = service()
    progressed, evidence_id, competency_id = recorded_plan(core)

    try:
        core.evaluate_evidence(
            state_token=progressed.state_token,
            verdict=verdict("evidence-does-not-exist", competency_id),
        )
    except UnknownEvidenceError:
        pass
    else:
        raise AssertionError("unknown trusted-evidence reference was accepted")

    other = next(item.id for item in progressed.role.competencies if item.id != competency_id)
    try:
        core.evaluate_evidence(
            state_token=progressed.state_token,
            verdict=verdict(evidence_id, other),
        )
    except EvidenceCompetencyMismatchError:
        pass
    else:
        raise AssertionError("competency-mismatched trusted verdict was accepted")


def test_schema_four_state_migrates_without_inventing_trusted_evidence() -> None:
    core = service()
    codec = SignedStateCodec(SECRET)
    progressed, _, competency_id = recorded_plan(core)
    state = codec.decode(progressed.state_token)
    legacy_record = state.evidence_history[-1].model_copy(update={"evidence_id": ""})
    legacy = state.model_copy(
        update={
            "schema_version": 4,
            "evidence_history": [legacy_record],
            "evidence_evaluations": [],
            "competency_evidence": {},
            "misconceptions": [],
            "review_state": {},
        }
    )

    migrated = core.resume(codec.encode(legacy))
    migrated_state = codec.decode(migrated.state_token)

    assert migrated_state.schema_version == 5
    assert migrated.evidence_history[-1].evidence_id.startswith("evidence-")
    assert evidence_status(migrated, competency_id).status == "unverified"
    assert migrated.evidence_evaluations == []
    assert migrated.verified_readiness_percent is None


def test_durable_trusted_evaluation_commits_a_versioned_evidence_event() -> None:
    async def scenario() -> None:
        repository = MemoryRepository()
        persistent = PersistentLearningService(
            secret=SECRET,
            repository=repository,
            clock=lambda: NOW,
        )
        created = await persistent.create_plan(
            account_id=ACCOUNT_ID,
            request=PersistentPlanCreateRequest(
                idempotency_key="g02-create-0000001",
                learner_name="Durable Evidence Learner",
                ratings=[],
            ),
        )
        assert created.plan.current_activity is not None
        progressed = await persistent.complete_activity(
            account_id=ACCOUNT_ID,
            request=PersistentProgressRequest(
                learner_id=UUID(created.plan.learner_id),
                expected_version=created.version,
                idempotency_key="g02-progress-000001",
                activity_id=created.plan.current_activity.id,
                reflection="Recorded work for later independent evaluation.",
                criteria_met=list(created.plan.current_activity.acceptance_criteria),
                confidence=2,
            ),
        )
        evidence = progressed.plan.evidence_history[-1]
        evaluated = await persistent.evaluate_evidence(
            account_id=ACCOUNT_ID,
            request=PersistentEvidenceEvaluationRequest(
                learner_id=UUID(progressed.plan.learner_id),
                expected_version=progressed.version,
                idempotency_key="g02-evaluate-000001",
                verdict=verdict(
                    evidence.evidence_id,
                    evidence.competency_id,
                    independence="independent",
                    assistance="none",
                    reasoning="verified",
                ),
            ),
        )

        assert evaluated.version == progressed.version + 1
        assert evidence_status(evaluated.plan, evidence.competency_id).status == "independent"
        assert repository.commits[-1].event_type == "learner.evidence.evaluated"
        assert evaluated.plan.verified_readiness_percent is None

    asyncio.run(scenario())


def test_public_api_does_not_expose_trusted_evaluator_write_route() -> None:
    app = create_app(
        Settings(
            environment="test",
            learner_state_secret=SecretStr(SECRET),
            log_level="CRITICAL",
        )
    )
    paths = app.openapi()["paths"]

    assert "/api/v1/evidence/evaluate" not in paths
    assert not any("trusted" in path and "evidence" in path for path in paths)
