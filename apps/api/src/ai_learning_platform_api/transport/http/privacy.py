"""Same-origin privacy controls for the current anonymous account."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from ai_learning_platform_api.learning.schemas import StrictModel
from ai_learning_platform_api.persistence.contracts import PersistenceUnavailableError

AccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Id", min_length=36, max_length=36),
]
DeleteAccount = Callable[[str], Awaitable[bool]]


class AccountDeletionRequest(StrictModel):
    """Explicit destructive-action confirmation."""

    confirmation: Literal["DELETE"]


class AccountDeletionView(StrictModel):
    """Deletion result without exposing internal storage records."""

    deleted: bool
    scope: Literal["current_anonymous_account"] = "current_anonymous_account"


def create_privacy_router(delete_account: DeleteAccount) -> APIRouter:
    """Create the anonymous-account data-control route."""
    router = APIRouter(prefix="/api/v1", tags=["privacy"])

    @router.delete("/account", response_model=AccountDeletionView)
    async def delete_current_account(
        request: AccountDeletionRequest,
        account_header: AccountHeader,
    ) -> AccountDeletionView:
        del request
        account_id = _uuid(account_header)
        try:
            deleted = await delete_account(account_id)
        except PersistenceUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "PERSISTENCE_UNAVAILABLE",
                    "message": "Account data could not be deleted right now.",
                },
            ) from error
        return AccountDeletionView(deleted=deleted)

    return router


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
