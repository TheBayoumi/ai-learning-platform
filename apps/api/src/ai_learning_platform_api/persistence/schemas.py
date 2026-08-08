"""Strict internal contracts for PostgreSQL-backed learner operations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field

from ai_learning_platform_api.learning.schemas import (
    AssessmentAnswer,
    AssessmentAttemptView,
    AssessmentSubmissionView,
    CompetencyRating,
    PlanView,
    StrictModel,
    TargetRequest,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceSubmission,
)

IdempotencyKey = Annotated[str, Field(min_length=16, max_length=160, pattern=r"^[^\s]+$")]


class PersistentPlanCreateRequest(StrictModel):
    """Create and atomically persist an initial deterministic learner plan."""

    idempotency_key: IdempotencyKey
    learner_name: Annotated[str, Field(min_length=2, max_length=80)]
    target_role: Annotated[str, Field(min_length=2, max_length=80)] = (
        "junior-python-backend-engineer"
    )
    target: TargetRequest | None = None
    weekly_hours: Annotated[int, Field(ge=2, le=40)] = 8
    experience_summary: Annotated[str, Field(min_length=0, max_length=600)] = ""
    ratings: Annotated[list[CompetencyRating], Field(max_length=32)] = Field(default_factory=list)


class PersistentPlanImportRequest(StrictModel):
    """Import one valid legacy signed state into the durable account boundary."""

    idempotency_key: IdempotencyKey
    state_token: Annotated[str, Field(min_length=20, max_length=65_536)]


class PersistentMutationRequest(StrictModel):
    """Common optimistic-concurrency fields for evidence-bearing commands."""

    learner_id: UUID
    expected_version: Annotated[int, Field(ge=0)]
    idempotency_key: IdempotencyKey


class PersistentProgressRequest(PersistentMutationRequest):
    """Record learner-attested work against a durable aggregate."""

    activity_id: Annotated[str, Field(min_length=1, max_length=160)]
    reflection: Annotated[str, Field(min_length=0, max_length=1_000)] = ""
    evidence_reference: Annotated[str, Field(min_length=0, max_length=500)] = ""
    criteria_met: Annotated[list[str], Field(max_length=16)] = Field(default_factory=list)
    confidence: Annotated[int, Field(ge=0, le=4)] = 0


class PersistentEvidenceEvaluationRequest(PersistentMutationRequest):
    """Commit one server-side trusted evaluator verdict to the durable aggregate."""

    verdict: TrustedEvidenceVerdict


class PersistentReplanRequest(PersistentMutationRequest):
    """Replan a durable aggregate under explicit capacity and focus changes."""

    weekly_hours: Annotated[int, Field(ge=2, le=40)]
    focus_competency_ids: Annotated[list[str], Field(max_length=4)] = Field(default_factory=list)


class PersistentAssessmentStartRequest(StrictModel):
    """Start a calibration attempt from the current durable aggregate."""

    learner_id: UUID
    question_count: Annotated[int, Field(ge=2, le=4)] = 4


class PersistentAssessmentSubmitRequest(PersistentMutationRequest):
    """Score and persist an assessment-informed planning transition."""

    attempt_token: Annotated[str, Field(min_length=20, max_length=16_384)]
    answers: Annotated[list[AssessmentAnswer], Field(min_length=1, max_length=4)]


class PersistentProbeEvaluationRequest(StrictModel):
    """Durable internal command for one trusted retention/transfer probe verdict."""

    learner_id: UUID
    expected_version: Annotated[int, Field(ge=0)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=160)]
    verdict: TrustedProbeVerdict


class PersistentWorkVerificationRequest(PersistentMutationRequest):
    """Issue post-artifact modification/debugging/defense challenges durably."""

    evidence_id: Annotated[str, Field(min_length=8, max_length=160)]


class PersistentWorkProvenanceSubmissionRequest(PersistentMutationRequest):
    """Capture immutable learner work provenance through the durable aggregate."""

    submission: WorkProvenanceSubmission


class PersistentWorkProvenanceEvaluationRequest(PersistentMutationRequest):
    """Commit one trusted authorship/modification/debugging/defense verdict."""

    verdict: TrustedWorkProvenanceVerdict


class PersistentPlanView(StrictModel):
    """A durable plan projection and its optimistic aggregate version."""

    plan: PlanView
    version: Annotated[int, Field(ge=0)]


class PersistentAssessmentSubmissionView(StrictModel):
    """Assessment feedback plus the newly committed aggregate version."""

    submission: AssessmentSubmissionView
    version: Annotated[int, Field(ge=0)]


class PersistentAssessmentAttemptView(StrictModel):
    """Compatibility envelope for a non-mutating durable assessment start."""

    attempt: AssessmentAttemptView
