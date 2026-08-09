"""Provider-neutral identity and authorization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

AccountRole = Literal["learner", "reviewer", "admin"]


class IdentityError(RuntimeError):
    """Base identity-boundary failure."""


class InvalidAccessTokenError(IdentityError):
    """The supplied OIDC access token is missing, malformed, expired, or untrusted."""


class IdentityUnavailableError(IdentityError):
    """The configured identity provider or identity store cannot be reached safely."""


class AnonymousClaimError(IdentityError):
    """An anonymous account cannot be migrated into the authenticated account."""


@dataclass(frozen=True, slots=True)
class OidcPrincipal:
    """Validated standard claims from one managed OIDC access token."""

    issuer: str
    subject: str
    email: str | None = None

    def __post_init__(self) -> None:
        if not self.issuer.startswith("https://") or len(self.issuer) > 512:
            raise ValueError("issuer must be one bounded HTTPS identifier")
        if not self.subject or len(self.subject) > 255 or self.subject != self.subject.strip():
            raise ValueError("subject must be one bounded canonical identifier")
        if self.email is not None and (len(self.email) > 320 or self.email != self.email.strip()):
            raise ValueError("email must be bounded and canonical")


@dataclass(frozen=True, slots=True)
class PlatformIdentity:
    """Stable platform account identity independent from the OIDC vendor."""

    account_id: str
    issuer: str
    subject: str
    roles: tuple[AccountRole, ...]

    def __post_init__(self) -> None:
        if not self.account_id or len(self.account_id) > 160:
            raise ValueError("account_id must be bounded")
        if not self.roles or "learner" not in self.roles:
            raise ValueError("every product identity must retain the learner role")
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("identity roles must be unique")


class OidcTokenVerifier(Protocol):
    """Validate a bearer token and return only provider-neutral principal claims."""

    async def verify(self, token: str) -> OidcPrincipal: ...

    async def aclose(self) -> None: ...


class IdentityRepository(Protocol):
    """Resolve provider identities and account roles into platform-owned identifiers."""

    async def resolve(self, principal: OidcPrincipal) -> PlatformIdentity: ...

    async def claim_anonymous_account(
        self,
        *,
        target_account_id: str,
        anonymous_account_id: str,
    ) -> bool: ...
