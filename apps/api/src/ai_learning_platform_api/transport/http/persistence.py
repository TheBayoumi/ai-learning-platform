"""HTTP transport for durable PostgreSQL-backed learner operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from ai_learning_platform_api.learning.assessment import AssessmentError
from ai_learning_platform_api.learning.service import LearningPlanError
from ai_learning_platform_api.persistence.contracts import (
    IdempotencyConflictError,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.persistence.schemas import (
    PersistentAssessmentAttemptView,
    PersistentAssessmentStartRequest,
    PersistentAssessmentSubmissionView,
    PersistentAssessmentSubmitRequest,
    PersistentPlanCreateRequest,
    PersistentPlanImportRequest,
    PersistentPlanView,
    PersistentProgressRequest,
    PersistentReplanRequest,
    PersistentResumeRequest,
    RuntimeCapabilitiesView,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.settings import PersistenceMode

T = TypeVar("T")
AccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Id", min_length=36, max_length=36),
]


def create_runtime_router(persistence_mode: PersistenceMode) -> APIRouter:
    """Expose a non-confidential capability contract for browser protocol selection."""
    router = APIRouter(prefix="/api/v1", tags=["runtime"])

    @router.get(
        "/runtime",
        response_model=RuntimeCapabilitiesView,
        operation_id="get_runtime_capabilities",
    )
    async def runtime_capabilities() -> RuntimeCapabilitiesView:
        return RuntimeCapabilitiesView(persistence_mode=persistence_mode)

    return router


def create_persistent_learning_router(service: PersistentLearningService) -> APIRouter:
    """Create durable routes with ownership, conflict, and availability failures."""
    router = APIRouter(prefix="/api/v1/persistent", tags=["persistent-learning"])

    @router.post(
        "/plans",
        response_model=PersistentPlanView,
        status_code=status.HTTP_201_CREATED,
        operation_id="create_persistent_plan",
    )
    async def create_plan(
        request: PersistentPlanCreateRequest,
        account_header: AccountHeader,
    ) -> PersistentPlanView:
        account_id = _account_id(account_header)
        return await _run(lambda: service.create_plan(account_id=account_id, request=request))

    @router.post(
        "/plans/import",
        response_model=PersistentPlanView,
        status_code=status.HTTP_201_CREATED,
        operation_id="import_persistent_plan",
    )
    async def import_plan(
        request: PersistentPlanImportRequest,
        account_header: AccountHeader,
    ) -> PersistentPlanView:
        account_id = _account_id(account_header)
        return await _run(lambda: service.import_plan(account_id=account_id, request=request))

    @router.post(
        "/plans/resume",
        response_model=PersistentPlanView,
        operation_id="resume_persistent_plan",
    )
    async def resume_plan(
        request: PersistentResumeRequest,
        account_header: AccountHeader,
    ) -> PersistentPlanView:
        account_id = _account_id(account_header)
        return await _run(
            lambda: service.resume_plan(account_id=account_id, learner_id=request.learner_id)
        )

    @router.post(
        "/plans/replan",
        response_model=PersistentPlanView,
        operation_id="replan_persistent_curriculum",
    )
    async def replan(
        request: PersistentReplanRequest,
        account_header: AccountHeader,
    ) -> PersistentPlanView:
        account_id = _account_id(account_header)
        return await _run(lambda: service.replan(account_id=account_id, request=request))

    @router.post(
        "/progress",
        response_model=PersistentPlanView,
        operation_id="complete_persistent_activity",
    )
    async def complete_activity(
        request: PersistentProgressRequest,
        account_header: AccountHeader,
    ) -> PersistentPlanView:
        account_id = _account_id(account_header)
        return await _run(
            lambda: service.complete_activity(account_id=account_id, request=request)
        )

    @router.post(
        "/assessments/start",
        response_model=PersistentAssessmentAttemptView,
        operation_id="start_persistent_assessment",
    )
    async def start_assessment(
        request: PersistentAssessmentStartRequest,
        account_header: AccountHeader,
    ) -> PersistentAssessmentAttemptView:
        account_id = _account_id(account_header)
        return await _run(
            lambda: service.start_assessment(account_id=account_id, request=request)
        )

    @router.post(
        "/assessments/submit",
        response_model=PersistentAssessmentSubmissionView,
        operation_id="submit_persistent_assessment",
    )
    async def submit_assessment(
        request: PersistentAssessmentSubmitRequest,
        account_header: AccountHeader,
    ) -> PersistentAssessmentSubmissionView:
        account_id = _account_id(account_header)
        return await _run(
            lambda: service.submit_assessment(account_id=account_id, request=request)
        )

    return router


async def _run(operation: Callable[[], Awaitable[T]]) -> T:
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
        code = (
            "LEARNER_STATE_CONFLICT"
            if isinstance(error, LearnerStateConflictError)
            else "IDEMPOTENCY_CONFLICT"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": code,
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


def _account_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_ACCOUNT_CONTEXT",
                "message": "The anonymous account context is invalid.",
            },
        ) from error
