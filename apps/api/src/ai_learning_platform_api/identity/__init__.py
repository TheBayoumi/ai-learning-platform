"""Managed identity boundary exports."""

from ai_learning_platform_api.identity.contracts import (
    AccountRole,
    AnonymousClaimError,
    IdentityRepository,
    IdentityUnavailableError,
    InvalidAccessTokenError,
    OidcPrincipal,
    OidcTokenVerifier,
    PlatformIdentity,
)
from ai_learning_platform_api.identity.middleware import OidcAccountMiddleware
from ai_learning_platform_api.identity.oidc import ManagedOidcVerifier
from ai_learning_platform_api.identity.postgres import PostgresIdentityRepository

__all__ = [
    "AccountRole",
    "AnonymousClaimError",
    "IdentityRepository",
    "IdentityUnavailableError",
    "InvalidAccessTokenError",
    "ManagedOidcVerifier",
    "OidcAccountMiddleware",
    "OidcPrincipal",
    "OidcTokenVerifier",
    "PlatformIdentity",
    "PostgresIdentityRepository",
]
