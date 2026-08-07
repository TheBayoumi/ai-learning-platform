from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI

from ai_learning_platform_api.persistence.contracts import PersistenceUnavailableError
from ai_learning_platform_api.transport.http.privacy import (
    DeleteAccount,
    create_privacy_router,
)

ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"


async def request(
    delete_account: DeleteAccount,
    *,
    account_id: str = ACCOUNT_ID,
    confirmation: str = "DELETE",
) -> httpx.Response:
    app = FastAPI()
    app.include_router(create_privacy_router(delete_account))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(
            "DELETE",
            "/api/v1/account",
            headers={"x-platform-account-id": account_id},
            json={"confirmation": confirmation},
        )


def test_privacy_router_deletes_only_header_owned_account() -> None:
    seen: list[str] = []

    async def delete_account(account_id: str) -> bool:
        seen.append(account_id)
        return True

    response = asyncio.run(request(delete_account))
    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "scope": "current_anonymous_account",
    }
    assert seen == [ACCOUNT_ID]


def test_privacy_router_is_idempotent_when_account_is_absent() -> None:
    async def delete_account(_: str) -> bool:
        return False

    response = asyncio.run(request(delete_account))
    assert response.status_code == 200
    assert response.json()["deleted"] is False


def test_privacy_router_rejects_invalid_confirmation_before_deletion() -> None:
    called = False

    async def delete_account(_: str) -> bool:
        nonlocal called
        called = True
        return True

    response = asyncio.run(request(delete_account, confirmation="delete"))
    assert response.status_code == 422
    assert called is False


def test_privacy_router_rejects_invalid_account_context() -> None:
    called = False

    async def delete_account(_: str) -> bool:
        nonlocal called
        called = True
        return True

    response = asyncio.run(request(delete_account, account_id="x" * 36))
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST_CONTEXT"
    assert called is False


def test_privacy_router_maps_storage_failure_without_details() -> None:
    async def delete_account(_: str) -> bool:
        raise PersistenceUnavailableError("database password must not leak")

    response = asyncio.run(request(delete_account))
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "PERSISTENCE_UNAVAILABLE",
        "message": "Account data could not be deleted right now.",
    }
    assert "password" not in response.text
