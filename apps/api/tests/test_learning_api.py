from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.settings import Settings

TEST_SECRET = "test-learner-state-secret-with-at-least-32-bytes"


async def request(method: str, path: str, json: object | None = None) -> httpx.Response:
    app = create_app(
        Settings(
            environment="test",
            log_level="CRITICAL",
            learner_state_secret=SecretStr(TEST_SECRET),
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json)


def test_role_catalog_exposes_versioned_python_backend_profile() -> None:
    response = asyncio.run(request("GET", "/api/v1/roles"))

    assert response.status_code == 200
    roles = response.json()
    assert len(roles) == 1
    assert roles[0]["id"] == "junior-python-backend-engineer"
    assert roles[0]["version"] == "2026.07-provisional-1"
    assert {item["id"] for item in roles[0]["competencies"]} >= {
        "python",
        "fastapi",
        "postgresql",
        "testing",
        "docker",
    }


def test_create_resume_and_complete_activity_round_trip() -> None:
    create_response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans",
            {
                "learner_name": "Mahmoud",
                "weekly_hours": 10,
                "experience_summary": "Automotive embedded engineer moving into backend AI systems",
                "ratings": [
                    {"competency_id": "python", "score": 2},
                    {"competency_id": "git", "score": 3},
                    {"competency_id": "testing", "score": 2},
                ],
            },
        )
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["learner_name"] == "Mahmoud"
    assert created["role"]["id"] == "junior-python-backend-engineer"
    assert created["readiness_percent"] > 0
    assert created["completed_count"] == 0
    assert created["total_count"] == 5
    assert created["current_activity"]["id"].startswith("activity-")
    assert "Mahmoud" in created["current_activity"]["objective"]

    resumed_response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans/resume",
            {"state_token": created["state_token"]},
        )
    )
    assert resumed_response.status_code == 200
    resumed = resumed_response.json()
    assert resumed["learner_id"] == created["learner_id"]
    assert resumed["current_activity"] == created["current_activity"]

    progress_response = asyncio.run(
        request(
            "POST",
            "/api/v1/progress",
            {
                "state_token": created["state_token"],
                "activity_id": created["current_activity"]["id"],
                "reflection": (
                    "I separated transport validation from the domain service and proved both "
                    "failure and success paths with focused tests."
                ),
            },
        )
    )
    assert progress_response.status_code == 200
    progressed = progress_response.json()
    assert progressed["completed_count"] == 1
    assert progressed["sequence"] == 1
    assert progressed["current_activity"]["id"] != created["current_activity"]["id"]
    assert progressed["readiness_percent"] >= created["readiness_percent"]
    assert progressed["state_token"] != created["state_token"]


def test_tampered_state_and_duplicate_ratings_fail_closed() -> None:
    create_response = asyncio.run(request("POST", "/api/v1/plans", {"learner_name": "Ahmed"}))
    token = create_response.json()["state_token"]
    replacement = "A" if token[-1] != "A" else "B"

    tampered = asyncio.run(
        request(
            "POST",
            "/api/v1/plans/resume",
            {"state_token": token[:-1] + replacement},
        )
    )
    assert tampered.status_code == 400
    assert tampered.json()["detail"]["code"] == "INVALID_STATE_TOKEN"

    duplicate = asyncio.run(
        request(
            "POST",
            "/api/v1/plans",
            {
                "learner_name": "Ahmed",
                "ratings": [
                    {"competency_id": "python", "score": 1},
                    {"competency_id": "python", "score": 2},
                ],
            },
        )
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "INVALID_COMPETENCY_RATING"


def test_learner_context_changes_unique_activity_identity() -> None:
    service = LearningPlanService(
        TEST_SECRET,
        clock=lambda: datetime(2026, 7, 23, tzinfo=UTC),
        id_factory=lambda: UUID("00000000-0000-0000-0000-000000000001"),
    )

    first = service.create_plan(PlanRequest(learner_name="Mona", experience_summary="QA engineer"))
    second = service.create_plan(
        PlanRequest(learner_name="Mona", experience_summary="Data analyst")
    )

    assert first.current_activity is not None
    assert second.current_activity is not None
    assert first.current_activity.id != second.current_activity.id
    assert first.current_activity.objective != second.current_activity.objective


def test_production_requires_a_real_signing_secret() -> None:
    with pytest.raises(ValidationError, match="production learner_state_secret"):
        Settings(environment="production")
