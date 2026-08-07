from __future__ import annotations

import asyncio

import httpx
from pydantic import SecretStr

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.settings import Settings

TEST_SECRET = "test-career-track-secret-with-at-least-thirty-two-bytes"


async def request(method: str, path: str, json_body: object | None = None) -> httpx.Response:
    app = create_app(
        Settings(
            environment="test",
            log_level="CRITICAL",
            learner_state_secret=SecretStr(TEST_SECRET),
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json_body)


def test_legacy_role_contract_stays_stable_while_career_catalog_expands() -> None:
    legacy = asyncio.run(request("GET", "/api/v1/roles"))
    catalog = asyncio.run(request("GET", "/api/v1/career-tracks"))

    assert legacy.status_code == 200
    assert [role["id"] for role in legacy.json()] == ["junior-python-backend-engineer"]

    assert catalog.status_code == 200
    roles = catalog.json()
    assert {role["id"] for role in roles} == {
        "junior-python-backend-engineer",
        "ai-application-engineer",
        "data-engineer",
    }
    assert all(sum(item["weight"] for item in role["competencies"]) == 100 for role in roles)
    assert all(len(role["competencies"]) >= 10 for role in roles)


def test_ai_application_track_creates_resumable_role_specific_work() -> None:
    created_response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans",
            {
                "learner_name": "AI Learner",
                "target_role": "ai-application-engineer",
                "weekly_hours": 10,
                "experience_summary": "Backend engineer moving into production LLM systems",
                "ratings": [
                    {"competency_id": "python", "score": 3},
                    {"competency_id": "llm-applications", "score": 1},
                    {"competency_id": "rag", "score": 0},
                    {"competency_id": "ai-evaluation", "score": 0},
                ],
            },
        )
    )

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["role"]["id"] == "ai-application-engineer"
    assert {item["id"] for item in created["role"]["competencies"]} >= {
        "llm-applications",
        "rag",
        "ai-evaluation",
    }
    assert created["current_activity"]["competency_id"] in {
        "llm-applications",
        "rag",
        "ai-evaluation",
        "fastapi",
        "testing",
    }

    resumed = asyncio.run(
        request(
            "POST",
            "/api/v1/plans/resume",
            {"state_token": created["state_token"]},
        )
    )
    assert resumed.status_code == 200
    assert resumed.json()["role"]["id"] == "ai-application-engineer"

    attempt = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/start",
            {"state_token": created["state_token"], "question_count": 4},
        )
    )
    assert attempt.status_code == 200
    rendered = attempt.text
    assert "correct_option" not in rendered
    assert "explanation" not in rendered
    assert len(attempt.json()["questions"]) == 4


def test_data_engineer_track_uses_data_specific_competency_graph() -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans",
            {
                "learner_name": "Data Learner",
                "target_role": "data-engineer",
                "weekly_hours": 7,
                "experience_summary": "Python developer adding analytical data engineering skills",
                "ratings": [
                    {"competency_id": "python", "score": 2},
                    {"competency_id": "postgresql", "score": 2},
                    {"competency_id": "data-modeling", "score": 0},
                    {"competency_id": "data-pipelines", "score": 0},
                    {"competency_id": "data-quality", "score": 0},
                ],
            },
        )
    )

    assert response.status_code == 201
    plan = response.json()
    assert plan["role"]["id"] == "data-engineer"
    assert {item["id"] for item in plan["role"]["competencies"]} >= {
        "data-modeling",
        "data-pipelines",
        "data-quality",
    }
    priority_ids = {item["id"] for item in plan["priority_competencies"][:6]}
    assert priority_ids & {"data-modeling", "data-pipelines", "data-quality"}
