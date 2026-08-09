from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from ai_learning_platform_api.identity.contracts import (
    IdentityUnavailableError,
    InvalidAccessTokenError,
)
from ai_learning_platform_api.identity.oidc import ManagedOidcVerifier

_ISSUER = "https://tenant.example/"
_AUDIENCE = "https://api.career-atlas.example"
_JWKS = "https://tenant.example/.well-known/jwks.json"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
_RAW_JWK = RSAAlgorithm.to_jwk(_PUBLIC_KEY)
_JWK: dict[str, Any] = json.loads(_RAW_JWK) if isinstance(_RAW_JWK, str) else _RAW_JWK
_JWK.update({"kid": "key-1", "alg": "RS256", "use": "sig"})


def _claims(*, audience: str = _AUDIENCE, issuer: str = _ISSUER) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "iss": issuer,
        "sub": "auth0|learner-1",
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "email": "learner@example.com",
    }


def _token(*, audience: str = _AUDIENCE, kid: str = "key-1") -> str:
    return jwt.encode(
        _claims(audience=audience),
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _client(*, discovery_issuer: str = _ISSUER, count: list[str] | None = None) -> httpx.AsyncClient:
    calls = [] if count is None else count

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if str(request.url) == f"{_ISSUER}.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={"issuer": discovery_issuer, "jwks_uri": _JWKS},
            )
        if str(request.url) == _JWKS:
            return httpx.Response(200, json={"keys": [_JWK]})
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_valid_token_is_verified_and_jwks_is_cached() -> None:
    calls: list[str] = []
    client = _client(count=calls)
    verifier = ManagedOidcVerifier(
        issuer=_ISSUER,
        audience=_AUDIENCE,
        client=client,
        clock=lambda: 10.0,
    )

    first = await verifier.verify(_token())
    second = await verifier.verify(_token())

    assert first == second
    assert first.subject == "auth0|learner-1"
    assert first.email == "learner@example.com"
    assert len(calls) == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_wrong_audience_and_unknown_key_fail_closed() -> None:
    client = _client()
    verifier = ManagedOidcVerifier(issuer=_ISSUER, audience=_AUDIENCE, client=client)

    with pytest.raises(InvalidAccessTokenError):
        await verifier.verify(_token(audience="https://wrong.example"))
    with pytest.raises(InvalidAccessTokenError):
        await verifier.verify(_token(kid="unknown"))
    await client.aclose()


@pytest.mark.asyncio
async def test_non_rs256_token_is_rejected_before_key_lookup() -> None:
    calls: list[str] = []
    client = _client(count=calls)
    verifier = ManagedOidcVerifier(issuer=_ISSUER, audience=_AUDIENCE, client=client)
    token = jwt.encode(_claims(), "not-a-production-secret", algorithm="HS256", headers={"kid": "key-1"})

    with pytest.raises(InvalidAccessTokenError):
        await verifier.verify(token)

    assert calls == []
    await client.aclose()


@pytest.mark.asyncio
async def test_discovery_issuer_mismatch_is_identity_outage_not_token_acceptance() -> None:
    client = _client(discovery_issuer="https://evil.example/")
    verifier = ManagedOidcVerifier(issuer=_ISSUER, audience=_AUDIENCE, client=client)

    with pytest.raises(IdentityUnavailableError):
        await verifier.verify(_token())
    await client.aclose()


def test_oidc_configuration_rejects_insecure_issuer_and_bad_cache() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        ManagedOidcVerifier(issuer="http://tenant.example", audience=_AUDIENCE)
    with pytest.raises(ValueError, match="cache"):
        ManagedOidcVerifier(issuer=_ISSUER, audience=_AUDIENCE, cache_seconds=1)
