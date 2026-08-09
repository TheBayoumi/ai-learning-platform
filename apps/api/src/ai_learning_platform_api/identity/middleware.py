"""ASGI authentication boundary that converts trusted OIDC identity into platform ownership."""

from __future__ import annotations

from collections.abc import Iterable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ai_learning_platform_api.identity.contracts import (
    IdentityRepository,
    IdentityUnavailableError,
    InvalidAccessTokenError,
    OidcTokenVerifier,
)

_PUBLIC_PATHS = frozenset(
    {
        "/health/live",
        "/health/ready",
        "/api/v1/roles",
        "/api/v1/career-tracks",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)
_ACCOUNT_HEADER = b"x-platform-account-id"
_ROLES_HEADER = b"x-platform-account-roles"


class OidcAccountMiddleware:
    """Ignore client account headers and derive platform ownership from a bearer token."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        verifier: OidcTokenVerifier,
        repository: IdentityRepository,
    ) -> None:
        self._app = app
        self._verifier = verifier
        self._repository = repository

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        if path in _PUBLIC_PATHS or not path.startswith("/api/v1/"):
            await self._app(scope, receive, send)
            return

        token = _bearer_token(scope.get("headers", []))
        if token is None:
            await _error(send, 401, "AUTHENTICATION_REQUIRED", "Sign in to continue.")
            return
        try:
            principal = await self._verifier.verify(token)
            identity = await self._repository.resolve(principal)
        except InvalidAccessTokenError:
            await _error(send, 401, "INVALID_ACCESS_TOKEN", "The sign-in session is invalid.")
            return
        except IdentityUnavailableError:
            await _error(
                send,
                503,
                "IDENTITY_UNAVAILABLE",
                "Identity verification is temporarily unavailable.",
            )
            return

        headers = [
            (name, value)
            for name, value in scope.get("headers", [])
            if name.lower() not in {_ACCOUNT_HEADER, _ROLES_HEADER}
        ]
        headers.append((_ACCOUNT_HEADER, identity.account_id.encode("ascii")))
        headers.append((_ROLES_HEADER, ",".join(identity.roles).encode("ascii")))
        authenticated_scope = dict(scope)
        authenticated_scope["headers"] = headers
        await self._app(authenticated_scope, receive, send)


async def _error(send: Send, status: int, code: str, message: str) -> None:
    response = JSONResponse(
        status_code=status,
        content={"detail": {"code": code, "message": message}},
        headers={"cache-control": "no-store", "x-content-type-options": "nosniff"},
    )

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    await response(
        {"type": "http", "http_version": "1.1", "method": "GET", "path": "/"},
        receive,
        send,
    )


def _bearer_token(headers: Iterable[tuple[bytes, bytes]]) -> str | None:
    for raw_name, raw_value in headers:
        if raw_name.lower() != b"authorization":
            continue
        try:
            value = raw_value.decode("ascii")
        except UnicodeDecodeError:
            return None
        scheme, separator, token = value.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token or token != token.strip():
            return None
        return token
    return None
