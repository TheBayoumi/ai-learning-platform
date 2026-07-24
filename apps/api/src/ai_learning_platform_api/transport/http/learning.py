"""HTTP transport for the learner diagnosis and progress slice."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ai_learning_platform_api.learning.schemas import (
    ApiError,
    PlanRequest,
    PlanView,
    ProgressRequest,
    ResumeRequest,
    RoleView,
)
from ai_learning_platform_api.learning.service import LearningPlanError, LearningPlanService


def create_learning_router(service: LearningPlanService) -> APIRouter:
    """Create product routes with stable, non-confidential error envelopes."""
    router = APIRouter(prefix="/api/v1", tags=["learning"])

    @router.get("/roles", response_model=list[RoleView], operation_id="list_roles")
    async def list_roles() -> list[RoleView]:
        return service.list_roles()

    @router.post(
        "/plans",
        response_model=PlanView,
        status_code=status.HTTP_201_CREATED,
        responses={400: {"model": ApiError}},
        operation_id="create_plan",
    )
    async def create_plan(request: PlanRequest) -> PlanView:
        return _run(lambda: service.create_plan(request))

    @router.post(
        "/plans/resume",
        response_model=PlanView,
        responses={400: {"model": ApiError}},
        operation_id="resume_plan",
    )
    async def resume_plan(request: ResumeRequest) -> PlanView:
        return _run(lambda: service.resume(request.state_token))

    @router.post(
        "/progress",
        response_model=PlanView,
        responses={400: {"model": ApiError}},
        operation_id="complete_activity",
    )
    async def complete_activity(request: ProgressRequest) -> PlanView:
        return _run(lambda: service.complete_activity(request))

    return router


def _run(operation: object) -> PlanView:
    if not callable(operation):
        raise TypeError("operation must be callable")
    try:
        result = operation()
    except LearningPlanError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": _safe_message(error)},
        ) from None
    if not isinstance(result, PlanView):
        raise TypeError("learning operation returned an invalid projection")
    return result


def _safe_message(error: LearningPlanError) -> str:
    messages = {
        "INVALID_STATE_TOKEN": "The saved learning session is invalid or has been modified.",
        "UNKNOWN_TARGET_ROLE": "The selected target role is not available.",
        "INVALID_COMPETENCY_RATING": "Competency ratings contain an unknown or duplicate item.",
        "UNKNOWN_ACTIVITY": "The selected activity does not belong to this learning plan.",
        "ACTIVITY_ALREADY_COMPLETED": "The selected activity is already completed.",
    }
    return messages.get(error.code, "The learning request could not be processed.")
