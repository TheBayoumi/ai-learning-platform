"""HTTP/SSE transport for bounded, non-authoritative tutor turns."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from ai_learning_platform_api.learning.assessment import AssessmentError
from ai_learning_platform_api.learning.service import LearningPlanError
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.tutoring.contracts import TutorTurnRequest
from ai_learning_platform_api.tutoring.gateway import TutorGatewayError
from ai_learning_platform_api.tutoring.limits import (
    TutorAdmissionError,
    TutorCapacityError,
    TutorRateLimitError,
    TutorTurnLease,
    TutorTurnLimiter,
)
from ai_learning_platform_api.tutoring.service import (
    PreparedTutorTurn,
    TutorService,
    TutorUnavailableError,
)

AccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Id", min_length=36, max_length=36),
]


def create_tutoring_router(
    service: TutorService,
    limiter: TutorTurnLimiter,
) -> APIRouter:
    """Create a streaming tutor endpoint with preflight state validation."""
    router = APIRouter(prefix="/api/v1", tags=["tutoring"])

    @router.post("/tutor/stream", operation_id="stream_tutor_turn")
    async def stream_tutor_turn(
        request: TutorTurnRequest,
        account_header: AccountHeader,
    ) -> StreamingResponse:
        account_id = _uuid(account_header)
        lease = await _admit(lambda: limiter.acquire(account_id))
        try:
            prepared = await _prepare(
                lambda: service.prepare(
                    account_id=account_id,
                    request=request,
                )
            )
        except Exception:
            await lease.release()
            raise
        return StreamingResponse(
            _events(service=service, prepared=prepared, lease=lease),
            media_type="text/event-stream",
            headers={
                "cache-control": "no-store",
                "x-accel-buffering": "no",
                "x-content-type-options": "nosniff",
            },
        )

    return router


async def _admit(
    operation: Callable[[], Awaitable[TutorTurnLease]],
) -> TutorTurnLease:
    try:
        return await operation()
    except TutorRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "TUTOR_RATE_LIMITED",
                "message": "Too many tutor turns were requested. Try again shortly.",
            },
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except TutorCapacityError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "TUTOR_BUSY",
                "message": "The tutor is at capacity. Try again shortly.",
            },
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except TutorAdmissionError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "TUTOR_ADMISSION_FAILED",
                "message": "The tutor cannot accept this turn right now.",
            },
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error


async def _prepare(
    operation: Callable[[], Awaitable[PreparedTutorTurn]],
) -> PreparedTutorTurn:
    try:
        return await operation()
    except TutorUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "TUTOR_UNAVAILABLE",
                "message": "The tutor is temporarily unavailable; your learning plan is safe.",
            },
        ) from error
    except LearnerStateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LEARNER_STATE_NOT_FOUND",
                "message": "The learning plan was not found.",
            },
        ) from error
    except LearnerStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LEARNER_STATE_CONFLICT",
                "message": "The learning plan changed. Reload it before asking the tutor.",
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
            detail={"code": error.code, "message": "The tutor request is invalid."},
        ) from error


async def _events(
    *,
    service: TutorService,
    prepared: PreparedTutorTurn,
    lease: TutorTurnLease,
) -> AsyncIterator[str]:
    try:
        yield _event(
            "meta",
            {
                "model": prepared.model,
                "prompt_version": prepared.prompt_version,
                "authoritative": False,
            },
        )
        produced_text = False
        try:
            async for delta in service.stream(prepared):
                produced_text = True
                yield _event("delta", {"text": delta})
            if not produced_text:
                raise TutorGatewayError("tutor provider produced no text")
            yield _event("done", {"status": "complete"})
        except TutorGatewayError:
            yield _event(
                "error",
                {
                    "code": "TUTOR_PROVIDER_UNAVAILABLE",
                    "message": (
                        "The tutor response was interrupted. Your learning state was not changed."
                    ),
                },
            )
    finally:
        await lease.release()


def _event(name: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {encoded}\n\n"


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
