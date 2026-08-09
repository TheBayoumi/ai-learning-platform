from __future__ import annotations

from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from ai_learning_platform_api.identity.contracts import (
    IdentityUnavailableError,
    InvalidAccessTokenError,
    OidcPrincipal,
    PlatformIdentity,
)
from ai_learning_platform_api.identity.middleware import OidcAccountMiddleware

_ACCOUNT = "11111111-1111-4111-8111-111111111111"


class _Verifier:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.tokens: list[str] = []

    async def verify(self, token: str) -> OidcPrincipal:
        self.tokens.append(token)
        if self.failure is not None:
            raise self.failure
        return OidcPrincipal(issuer="https://tenant.example/", subject="auth0|1")

    async def aclose(self) -> None:
        return None


class _Repository:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def resolve(self, principal: OidcPrincipal) -> PlatformIdentity:
        if self.failure is not None:
            raise self.failure
        return PlatformIdentity(
            account_id=_ACCOUNT,
            issuer=principal.issuer,
            subject=principal.subject,
            roles=("learner",),
        )

    async def claim_anonymous_account(
        self,
        *,
        identity: PlatformIdentity,
        anonymous_account_id: str,
    ) -> bool:
        del identity, anonymous_account_id
        return True


def _client(
    *,
    verifier_failure: Exception | None = None,
    repository_failure: Exception | None = None,
) -> tuple[TestClient, _Verifier]:
    app = FastAPI()

    @app.get("/api/v1/private")
    async def private(
        x_platform_account_id: str | None = Header(default=None),
        x_platform_account_roles: str | None = Header(default=None),
    ) -> dict[str, str | None]:
        return {
            "account": x_platform_account_id,
            "roles": x_platform_account_roles,
        }

    @app.get("/api/v1/roles")
    async def roles() -> dict[str, str]:
        return {"status": "public"}

    verifier = _Verifier(verifier_failure)
    app.add_middleware(
        OidcAccountMiddleware,
        verifier=verifier,
        repository=_Repository(repository_failure),
    )
    return TestClient(app), verifier


def test_authenticated_request_overwrites_forged_account_header() -> None:
    client, verifier = _client()
    response = client.get(
        "/api/v1/private",
        headers={
            "Authorization": "Bearer verified-token",
            "X-Platform-Account-Id": "99999999-9999-4999-8999-999999999999",
            "X-Platform-Account-Roles": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"account": _ACCOUNT, "roles": "learner"}
    assert verifier.tokens == ["verified-token"]


def test_missing_or_invalid_token_is_unauthorized() -> None:
    client, _ = _client()
    missing = client.get("/api/v1/private")
    assert missing.status_code == 401
    assert missing.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"

    invalid_client, _ = _client(verifier_failure=InvalidAccessTokenError())
    invalid = invalid_client.get("/api/v1/private", headers={"Authorization": "Bearer bad"})
    assert invalid.status_code == 401
    assert invalid.json()["detail"]["code"] == "INVALID_ACCESS_TOKEN"


def test_identity_store_outage_fails_closed() -> None:
    client, _ = _client(repository_failure=IdentityUnavailableError())
    response = client.get("/api/v1/private", headers={"Authorization": "Bearer valid"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "IDENTITY_UNAVAILABLE"


def test_public_catalog_path_does_not_require_bearer_token() -> None:
    client, verifier = _client()
    response = client.get("/api/v1/roles")

    assert response.status_code == 200
    assert response.json() == {"status": "public"}
    assert verifier.tokens == []
