from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning.schemas import (
    CompetencyRating,
    PlanRequest,
    ProgressRequest,
    TargetRequest,
)
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit, StoredLearnerState
from ai_learning_platform_api.persistence.schemas import PersistentPlanCreateRequest
from ai_learning_platform_api.persistence.service import PersistentLearningService

TEST_SECRET = "claim-integrity-secret-with-at-least-thirty-two-bytes"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"


class MemoryRepository:
    def __init__(self) -> None:
        self.values: dict[tuple[str, UUID], StoredLearnerState] = {}

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return self.values.get((account_id, learner_id))

    async def delete_account(self, *, account_id: str) -> bool:
        identities = [identity for identity in self.values if identity[0] == account_id]
        for identity in identities:
            del self.values[identity]
        return bool(identities)

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
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
        return stored


def _service() -> LearningPlanService:
    return LearningPlanService(
        TEST_SECRET,
        clock=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
        id_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
    )


def _resolved_target() -> TargetRequest:
    return TargetRequest(
        seniority="Junior individual contributor",
        labor_market="Egypt local and English-speaking remote roles",
        timeline_weeks=20,
        geography="Egypt / MENA",
        stack_overlays=["Python", "FastAPI", "PostgreSQL"],
        industry_overlay="Automotive technology",
        company_overlay=None,
    )


def test_self_report_and_attested_completion_never_grant_mastery_or_readiness() -> None:
    service = _service()
    codec = SignedStateCodec(TEST_SECRET)
    created = service.create_plan(
        PlanRequest(
            learner_name="Mona",
            target_role="junior-python-backend-engineer",
            target=_resolved_target(),
            ratings=[CompetencyRating(competency_id="python", score=4)],
        )
    )

    created_state = codec.decode(created.state_token)
    assert created.target.seniority == "Junior individual contributor"
    assert created.target.industry_overlay == "Automotive technology"
    assert created.claim_state == "validation_locked"
    assert created.verified_readiness_percent is None
    assert created.planning_signal_percent > 0
    assert created_state.schema_version == 5
    assert created_state.planning_signal["python"] == 100
    assert created_state.mastery == {}
    assert all(
        item.status == "unverified"
        for item in created_state.competency_evidence.values()
    )

    assert created.current_activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=created.state_token,
            activity_id=created.current_activity.id,
            reflection=(
                "I built the requested deliverable, recorded the trade-offs, and can point to the "
                "implementation, but this submission has not been independently verified."
            ),
            criteria_met=list(created.current_activity.acceptance_criteria),
            confidence=4,
        )
    )

    progressed_state = codec.decode(progressed.state_token)
    assert progressed.claim_state == "validation_locked"
    assert progressed.verified_readiness_percent is None
    assert progressed.evidence_history[-1].planning_signal_delta > 0
    assert progressed_state.mastery == {}
    assert progressed_state.planning_signal[created.current_activity.competency_id] > 0
    assert all(
        item.status == "unverified"
        for item in progressed_state.competency_evidence.values()
    )


def test_legacy_schema_three_mastery_is_migrated_only_to_planning_signal() -> None:
    service = _service()
    codec = SignedStateCodec(TEST_SECRET)
    current = service.create_plan(PlanRequest(learner_name="Legacy Learner"))
    state = codec.decode(current.state_token)
    legacy = state.model_copy(
        update={
            "schema_version": 3,
            "target": None,
            "planning_signal": {},
            "mastery": {"python": 75},
        }
    )

    resumed = service.resume(codec.encode(legacy))
    migrated = codec.decode(resumed.state_token)

    assert resumed.claim_state == "validation_locked"
    assert resumed.verified_readiness_percent is None
    assert resumed.target.role_id == "junior-python-backend-engineer"
    assert migrated.schema_version == 5
    assert migrated.planning_signal == {"python": 75}
    assert migrated.mastery == {}
    assert migrated.evidence_evaluations == []
    assert all(
        item.status == "unverified" for item in migrated.competency_evidence.values()
    )


def test_durable_creation_accepts_non_python_tracks_and_persists_resolved_target() -> None:
    async def scenario() -> None:
        persistent = PersistentLearningService(
            secret=TEST_SECRET,
            repository=MemoryRepository(),
            clock=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
        )
        created = await persistent.create_plan(
            account_id=ACCOUNT_ID,
            request=PersistentPlanCreateRequest(
                idempotency_key="claim-integrity-create-001",
                learner_name="AI Learner",
                target_role="ai-application-engineer",
                target=TargetRequest(
                    seniority="Junior AI application engineer",
                    labor_market="English-speaking remote product teams",
                    timeline_weeks=24,
                    geography="Egypt / remote",
                    stack_overlays=["Python", "FastAPI", "RAG", "AI evaluation"],
                ),
                weekly_hours=10,
                ratings=[],
            ),
        )

        assert created.plan.role.id == "ai-application-engineer"
        assert created.plan.target.role_id == "ai-application-engineer"
        assert created.plan.claim_state == "validation_locked"
        assert created.plan.verified_readiness_percent is None

    asyncio.run(scenario())
