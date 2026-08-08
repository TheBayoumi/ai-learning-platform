"""Compatibility transport that makes existing learning routes PostgreSQL-authoritative."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from ai_learning_platform_api.learning.assessment import AssessmentError
from ai_learning_platform_api.learning.schemas import (
    AssessmentAttemptView,
    AssessmentStartRequest,
    AssessmentSubmissionView,
    AssessmentSubmitRequest,
    PlanRequest,
    PlanView,
    ProgressRequest,
    ReplanRequest,
    ResumeRequest,
    RoleView,
)
from ai_learning_platform_api.learning.service import (
    LearningPlanError,
    LearningPlanService,
    SignedStateCodec,
)
from ai_learning_platform_api.persistence.contracts import (
    IdempotencyConflictError,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.persistence.schemas import (
    PersistentAssessmentStartRequest,
    PersistentAssessmentSubmitRequest,
    PersistentPlanCreateRequest,
    PersistentPlanImportRequest,
    PersistentPlanView,
    PersistentProgressRequest,
    PersistentReplanRequest,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

AccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Id", min_length=36, max_length=36),
]
CommandHeader = Annotated[
    str,
    Header(alias="X-Platform-Command-Id", min_length=36, max_length=36),
]


class PersistentCompatibilityService:
    """Translate the existing signed-state API into durable commands."""

    def __init__(self, *, secret: str, persistent: PersistentLearningService) -> None:
        self._core = LearningPlanService(secret)
        self._codec = SignedStateCodec(secret)
        self._persistent = persistent

    def list_roles(self) -> list[RoleView]:
        return self._core.list_roles()

    async def current_plan(self, *, account_id: str, state_token: str) -> PlanView:
        """Return the ownership-checked exact durable plan for a read-only operation."""
        return (await self._current(account_id=account_id, state_token=state_token)).plan

    async def create_plan(
        self,
        *,
        account_id: str,
        command_id: str,
        request: PlanRequest,
    ) -> PlanView:
        result = await self._persistent.create_plan(
            account_id=account_id,
            request=PersistentPlanCreateRequest(
                idempotency_key=command_id,
                **request.model_dump(),
            ),
        )
        return result.plan

    async def resume_plan(
        self,
        *,
        account_id: str,
        command_id: str,
        request: ResumeRequest,
    ) -> PlanView:
        state = self._codec.decode(request.state_token)
        learner_id = UUID(state.learner_id)
        try:
            result = await self._persistent.resume_plan(
                account_id=account_id,
                learner_id=learner_id,
            )
        except LearnerStateNotFoundError:
            result = await self._persistent.import_plan(
                account_id=account_id,
                request=PersistentPlanImportRequest(
                    idempotency_key=command_id,
                    state_token=request.state_token,
                ),
            )
        return result.plan

    async def complete_activity(
        self,
        *,
        account_id: str,
        command_id: str,
        request: ProgressRequest,
    ) -> PlanView:
        current = await self._current(account_id=account_id, state_token=request.state_token)
        result = await self._persistent.complete_activity(
            account_id=account_id,
            request=PersistentProgressRequest(
                learner_id=UUID(current.plan.learner_id),
                expected_version=current.version,
                idempotency_key=command_id,
                activity_id=request.activity_id,
                reflection=request.reflection,
                evidence_reference=request.evidence_reference,
                criteria_met=request.criteria_met,
                confidence=request.confidence,
            ),
        )
        return result.plan

    async def replan(
        self,
        *,
        account_id: str,
        command_id: str,
        request: ReplanRequest,
    ) -> PlanView:
        current = await self._current(account_id=account_id, state_token=request.state_token)
        result = await self._persistent.replan(
            account_id=account_id,
            request=PersistentReplanRequest(
                learner_id=UUID(current.plan.learner_id),
                expected_version=current.version,
                idempotency_key=command_id,
                weekly_hours=request.weekly_hours,
                focus_competency_ids=request.focus_competency_ids,
            ),
        )
        return result.plan

    async def start_assessment(
        self,
        *,
        account_id: str,
        request: AssessmentStartRequest,
    ) -> AssessmentAttemptView:
        current = await self._current(account_id=account_id, state_token=request.state_token)
        result = await self._persistent.start_assessment(
            account_id=account_id,
            request=PersistentAssessmentStartRequest(
                learner_id=UUID(current.plan.learner_id),
                question_count=request.question_count,
            ),
        )
        return result.attempt

    async def submit_assessment(
        self,
        *,
        account_id: str,
        command_id: str,
        request: AssessmentSubmitRequest,
    ) -> AssessmentSubmissionView:
        current = await self._current(account_id=account_id, state_token=request.state_token)
        result = await self._persistent.submit_assessment(
            account_id=account_id,
            request=PersistentAssessmentSubmitRequest(
                learner_id=UUID(current.plan.learner_id),
                expected_version=current.version,
                idempotency_key=command_id,
                attempt_token=request.attempt_token,
                answers=request.answers,
            ),
        )
        return result.submission

    async def _current(
        self,
        *,
        account_id: str,
        state_token: str,
    ) -> PersistentPlanView:
        supplied_plan = self._core.resume(state_token)
        supplied_state = self._codec.decode(supplied_plan.state_token)
        current = await self._persistent.resume_plan(
            account_id=account_id,
            learner_id=UUID(supplied_state.learner_id),
        )
        current_state = self._codec.decode(current.plan.state_token)
        if current_state != supplied_state:
            raise LearnerStateConflictError
        return current


def create_persistent_compatibility_router(
    service: PersistentCompatibilityService,
) -> APIRouter:
    """Expose the existing API surface with durable ownership semantics."""
    router = APIRouter(prefix="/api/v1", tags=["learning"])

    @router.get("/roles", response_model=list[RoleView], operation_id="list_roles")
    async def list_roles() -> list[RoleView]:
        """Keep the original published role endpoint backward compatible."""
        return service.list_roles()[:1]

    @router.get(
        "/career-tracks",
        response_model=list[RoleView],
        operation_id="list_career_tracks",
    )
    async def list_career_tracks() -> list[RoleView]:
        """Return the complete durable-mode career catalog used by the routed application."""
        return service.list_roles()

    @router.post("/plans", response_model=PlanView, status_code=status.HTTP_201_CREATED)
    async def create_plan(
        request: PlanRequest,
        account_header: AccountHeader,
        command_header: CommandHeader,
    ) -> PlanView:
        return await _run(
            lambda: service.create_plan(
                account_id=_uuid(account_header),
                command_id=_uuid(command_header),
                request=request,
            )
        )

    @router.post("/plans/resume", response_model=PlanView)
    async def resume_plan(
        request: ResumeRequest,
        account_header: AccountHeader,
        command_header: CommandHeader,
    ) -> PlanView:
        return await _run(
            lambda: service.resume_plan(
                account_id=_uuid(account_header),
                command_id=_uuid(command_header),
                request=request,
            )
        )

    @router.post("/plans/replan", response_model=PlanView)
    async def replan(
        request: ReplanRequest,
        account_header: AccountHeader,
        command_header: CommandHeader,
    ) -> PlanView:
        return await _run(
            lambda: service.replan(
                account_id=_uuid(account_header),
                command_id=_uuid(command_header),
                request=request,
            )
        )

    @router.post("/progress", response_model=PlanView)
    async def complete_activity(
        request: ProgressRequest,
        account_header: AccountHeader,
        command_header: CommandHeader,
    ) -> PlanView:
        return await _run(
            lambda: service.complete_activity(
                account_id=_uuid(account_header),
                command_id=_uuid(command_header),
                request=request,
            )
        )

    @router.post("/assessments/start", response_model=AssessmentAttemptView)
    async def start_assessment(
        request: AssessmentStartRequest,
        account_header: AccountHeader,
    ) -> AssessmentAttemptView:
        return await _run(
            lambda: service.start_assessment(
                account_id=_uuid(account_header),
                request=request,
            )
        )

    @router.post("/assessments/submit", response_model=AssessmentSubmissionView)
    async def submit_assessment(
        request: AssessmentSubmitRequest,
        account_header: AccountHeader,
        command_header: CommandHeader,
    ) -> AssessmentSubmissionView:
        return await _run(
            lambda: service.submit_assessment(
                account_id=_uuid(account_header),
                command_id=_uuid(command_header),
                request=request,
            )
        )

    return router


async def _run[T](operation: Callable[[], Awaitable[T]]) -> T:
    try:
        return await operation()
    except LearnerStateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LEARNER_STATE_NOT_FOUND",
                "message": "The learning plan was not found.",
            },
        ) from error
    except (LearnerStateConflictError, IdempotencyConflictError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LEARNER_STATE_CONFLICT",
                "message": "The learning plan changed. Reload it before retrying this action.",
            },
        ) from error
    except PersistenceUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PERSISTENCE_UNAVAILABLE",
                "message": "Durable learning storage is temporarily unavailable.",
            },
        ) from error
    except (LearningPlanError, AssessmentError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": "The learning request is invalid."},
        ) from error


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_REQUEST_CONTEXT",
                "message": "The request context is invalid.",
            },
        ) from error
