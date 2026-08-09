"""Generic managed-OIDC access-token verification with bounded discovery/JWKS caching."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlparse

import httpx
import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidTokenError

from ai_learning_platform_api.identity.contracts import (
    IdentityUnavailableError,
    InvalidAccessTokenError,
    OidcPrincipal,
)

Clock = Callable[[], float]
_ALLOWED_ALGORITHM = "RS256"
_MAX_TOKEN_BYTES = 16_384
_MAX_JWKS_KEYS = 32


@dataclass(frozen=True, slots=True)
class _CachedKeys:
    expires_at: float
    keys: dict[str, Any]


class ManagedOidcVerifier:
    """Verify standard OIDC access tokens without leaking provider SDKs into domain code."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        timeout_seconds: float = 5.0,
        cache_seconds: int = 300,
        client: httpx.AsyncClient | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        self._issuer = _canonical_issuer(issuer)
        if not audience or len(audience) > 512 or audience != audience.strip():
            raise ValueError("OIDC audience must be one bounded canonical identifier")
        if cache_seconds < 30 or cache_seconds > 3600:
            raise ValueError("OIDC JWKS cache must be between 30 and 3600 seconds")
        self._audience = audience
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )
        self._owns_client = client is None
        self._cached: _CachedKeys | None = None

    async def verify(self, token: str) -> OidcPrincipal:
        """Validate signature, issuer, audience, time claims, algorithm, and subject."""
        if not token or len(token.encode("utf-8")) > _MAX_TOKEN_BYTES:
            raise InvalidAccessTokenError
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as error:
            raise InvalidAccessTokenError from error
        algorithm = header.get("alg")
        key_id = header.get("kid")
        if algorithm != _ALLOWED_ALGORITHM or not isinstance(key_id, str) or not key_id:
            raise InvalidAccessTokenError

        key = await self._key(key_id)
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[_ALLOWED_ALGORITHM],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except InvalidTokenError as error:
            # One refresh handles routine managed-provider key rotation without accepting an
            # unverified token. A second failure is terminal for this request.
            self._cached = None
            key = await self._key(key_id)
            try:
                claims = jwt.decode(
                    token,
                    key=key,
                    algorithms=[_ALLOWED_ALGORITHM],
                    audience=self._audience,
                    issuer=self._issuer,
                    options={"require": ["exp", "iat", "iss", "sub", "aud"]},
                )
            except InvalidTokenError as retry_error:
                raise InvalidAccessTokenError from retry_error
        subject = claims.get("sub")
        issuer = claims.get("iss")
        email = claims.get("email")
        if not isinstance(subject, str) or not isinstance(issuer, str):
            raise InvalidAccessTokenError
        if email is not None and not isinstance(email, str):
            email = None
        try:
            return OidcPrincipal(issuer=issuer, subject=subject, email=email)
        except ValueError as error:
            raise InvalidAccessTokenError from error

    async def _key(self, key_id: str) -> Any:
        cached = self._cached
        now = self._clock()
        if cached is None or cached.expires_at <= now:
            cached = await self._refresh_keys(now)
        key = cached.keys.get(key_id)
        if key is None:
            cached = await self._refresh_keys(now)
            key = cached.keys.get(key_id)
        if key is None:
            raise InvalidAccessTokenError
        return key

    async def _refresh_keys(self, now: float) -> _CachedKeys:
        try:
            discovery_response = await self._client.get(
                f"{self._issuer}.well-known/openid-configuration"
            )
            discovery_response.raise_for_status()
            discovery = discovery_response.json()
            if not isinstance(discovery, dict):
                raise ValueError
            if discovery.get("issuer") != self._issuer:
                raise ValueError
            jwks_uri = discovery.get("jwks_uri")
            if not isinstance(jwks_uri, str) or not _is_https_url(jwks_uri):
                raise ValueError
            response = await self._client.get(jwks_uri)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError
            raw_keys = payload.get("keys")
            if not isinstance(raw_keys, list) or not 1 <= len(raw_keys) <= _MAX_JWKS_KEYS:
                raise ValueError
            keys: dict[str, Any] = {}
            for raw in raw_keys:
                if not isinstance(raw, dict) or raw.get("alg") not in {None, _ALLOWED_ALGORITHM}:
                    continue
                key_id = raw.get("kid")
                if not isinstance(key_id, str) or not key_id:
                    continue
                jwk = PyJWK.from_dict(cast(dict[str, Any], raw), algorithm=_ALLOWED_ALGORITHM)
                keys[key_id] = jwk.key
            if not keys:
                raise ValueError
        except (httpx.HTTPError, ValueError, TypeError, InvalidTokenError) as error:
            raise IdentityUnavailableError from error
        refreshed = _CachedKeys(expires_at=now + self._cache_seconds, keys=keys)
        self._cached = refreshed
        return refreshed

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _canonical_issuer(value: str) -> str:
    if not _is_https_url(value):
        raise ValueError("OIDC issuer must be HTTPS")
    normalized = value if value.endswith("/") else f"{value}/"
    if len(normalized) > 512:
        raise ValueError("OIDC issuer is too long")
    return normalized


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.username is None
