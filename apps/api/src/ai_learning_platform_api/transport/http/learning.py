"""HTTP transport for learner diagnosis, evidence, assessment, and replanning."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, HTTPException, status

from ai_learning_platform_api.learning.assessment import AssessmentError
from ai_learning_platform_api.learning.schemas import (
    ApiError,
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
from ai_learning_platform_api.learning.service import LearningPlanError, LearningPlanService

T = TypeVar("T")


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
        "/plans/replan",
        response_model=PlanView,
        responses={400: {"model": ApiError}},
        operation_id="replan_curriculum",
    )
    async def replan_curriculum(request: ReplanRequest) -> PlanView:
        return _run(lambda: service.replan(request))

    @router.post(
        "/progress",
        response_model=PlanView,
        responses={400: {"model": ApiError}},
        operation_id="complete_activity",
    )
    async def complete_activity(request: ProgressRequest) -> PlanView:
        return _run(lambda: service.complete_activity(request))

    @router.post(
        "/assessments/start",
        response_model=AssessmentAttemptView,
        responses={400: {"model": ApiError}},
        operation_id="start_assessment",
    )
    async def start_assessment(request: AssessmentStartRequest) -> AssessmentAttemptView:
        return _run(lambda: service.start_assessment(request))

    @router.post(
        "/assessments/submit",
        response_model=AssessmentSubmissionView,
        responses={400: {"model": ApiError}},
        operation_id="submit_assessment",
    )
    async def submit_assessment(request: AssessmentSubmitRequest) -> AssessmentSubmissionView:
        return _run(lambda: service.submit_assessment(request))

    return router


def _run(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except (LearningPlanError, AssessmentError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": _safe_message(error.code)},
        ) from None


def _safe_message(code: str) -> str:
    messages = {
        "INVALID_STATE_TOKEN": "The saved learning session is invalid or has been modified.",
        "UNKNOWN_TARGET_ROLE": "The selected target role is not available.",
        "INVALID_COMPETENCY_RATING": "Competency ratings contain an unknown or duplicate item.",
        "UNKNOWN_ACTIVITY": "The selected activity does not belong to this learning plan.",
        "ACTIVITY_ALREADY_COMPLETED": "The selected activity is already completed.",
        "INVALID_EVIDENCE": (
            "The evidence submission contains a duplicate or unknown acceptance criterion."
        ),
        "INVALID_REPLAN_FOCUS": (
            "The requested curriculum focus contains a duplicate or unknown competency."
        ),
        "INVALID_ASSESSMENT_ATTEMPT": (
            "The calibration attempt is invalid, expired, or does not match this learning state."
        ),
        "INVALID_ASSESSMENT_ANSWER": (
            "Assessment answers are incomplete, duplicated, or contain an unavailable option."
        ),
    }
    return messages.get(code, "The learning request could not be processed.")
