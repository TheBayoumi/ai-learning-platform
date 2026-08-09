"""Authenticated account/session transport for managed-OIDC product mode."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from ai_learning_platform_api.identity.claim import AnonymousAccountClaimProof
from ai_learning_platform_api.identity.contracts import AnonymousClaimError, IdentityUnavailableError
from ai_learning_platform_api.learning.schemas import PlanView, StrictModel
from ai_learning_platform_api.persistence.contracts import PersistenceUnavailableError

AccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Id", min_length=36, max_length=36),
]
RolesHeader = Annotated[
    str,
    Header(alias="X-Platform-Account-Roles", min_length=7, max_length=80),
]
AnonymousAccountHeader = Annotated[
    str,
    Header(alias="X-Platform-Anonymous-Account-Id", min_length=36, max_length=36),
]
AnonymousClaimHeader = Annotated[
    str,
    Header(alias="X-Platform-Anonymous-Claim", min_length=64, max_length=64),
]
ListPlans = Callable[[str], Awaitable[list[PlanView]]]
ClaimAnonymous = Callable[[str, str], Awaitable[bool]]


class IdentityView(StrictModel):
    """Non-sensitive account/session projection."""

    authenticated: bool = True
    roles: list[str]


class AnonymousClaimView(StrictModel):
    """One-time migration outcome for an existing anonymous learner account."""

    claimed: bool


def create_identity_router(
    *,
    list_plans: ListPlans,
    claim_anonymous: ClaimAnonymous,
    claim_proof: AnonymousAccountClaimProof,
) -> APIRouter:
    """Expose authenticated account continuity without trusting browser account selection."""
    router = APIRouter(prefix="/api/v1", tags=["identity"])

    @router.get("/identity/me", response_model=IdentityView)
    async def identity_me(
        account_header: AccountHeader,
        roles_header: RolesHeader,
    ) -> IdentityView:
        _uuid(account_header)
        roles = [role for role in roles_header.split(",") if role]
        if "learner" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "IDENTITY_ROLE_INVALID", "message": "Account access is invalid."},
            )
        return IdentityView(roles=roles)

    @router.get("/account/plans", response_model=list[PlanView])
    async def account_plans(account_header: AccountHeader) -> list[PlanView]:
        account_id = _uuid(account_header)
        try:
            return await list_plans(account_id)
        except PersistenceUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "PERSISTENCE_UNAVAILABLE",
                    "message": "Owned learning plans could not be loaded right now.",
                },
            ) from error

    @router.post("/account/claim-anonymous", response_model=AnonymousClaimView)
    async def claim_anonymous_account(
        account_header: AccountHeader,
        anonymous_account_header: AnonymousAccountHeader,
        anonymous_claim_header: AnonymousClaimHeader,
    ) -> AnonymousClaimView:
        target_account_id = _uuid(account_header)
        anonymous_account_id = _uuid(anonymous_account_header)
        if not claim_proof.verify(anonymous_account_id, anonymous_claim_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ANONYMOUS_CLAIM_INVALID",
                    "message": "Anonymous account migration proof is invalid.",
                },
            )
        try:
            claimed = await claim_anonymous(target_account_id, anonymous_account_id)
        except AnonymousClaimError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ANONYMOUS_CLAIM_CONFLICT",
                    "message": "Anonymous learner history cannot be claimed by this account.",
                },
            ) from error
        except IdentityUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "IDENTITY_UNAVAILABLE",
                    "message": "Account migration is temporarily unavailable.",
                },
            ) from error
        return AnonymousClaimView(claimed=claimed)

    return router


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST_CONTEXT", "message": "Request context is invalid."},
        ) from error
