from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.learning.schemas import PlanRequest, ProgressRequest, ReplanRequest
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
    assert roles[0]["validation_state"] == "provisional"
    assert roles[0]["default_target"]["role_id"] == "junior-python-backend-engineer"
    assert roles[0]["default_target"]["timeline_weeks"] == 20
    assert {item["id"] for item in roles[0]["competencies"]} >= {
        "python",
        "fastapi",
        "postgresql",
        "testing",
        "docker",
    }


def test_create_resume_and_complete_evidence_cycle_round_trip() -> None:
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
    current = created["current_activity"]
    assert created["learner_name"] == "Mahmoud"
    assert created["role"]["id"] == "junior-python-backend-engineer"
    assert created["target"]["role_version"] == "2026.07-provisional-1"
    assert created["claim_state"] == "validation_locked"
    assert created["verified_readiness_percent"] is None
    assert created["planning_signal_percent"] > 0
    assert created["completed_count"] == 0
    assert created["total_count"] == 5
    assert created["plan_revision"] == 0
    assert created["weekly_hours"] == 10
    assert created["evidence_history"] == []
    assert current["id"].startswith("activity-build-")
    assert current["kind"] == "build"
    assert current["rationale"]
    assert "not verified mastery" in current["rationale"]
    assert "Mahmoud" in current["objective"]

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
    assert resumed["current_activity"] == current

    progress_response = asyncio.run(
        request(
            "POST",
            "/api/v1/progress",
            {
                "state_token": created["state_token"],
                "activity_id": current["id"],
                "reflection": (
                    "I separated transport validation from the domain service and proved both "
                    "failure and success paths with focused tests and an explicit error contract."
                ),
                "evidence_reference": "https://github.com/example/typed-service/pull/7",
                "criteria_met": current["acceptance_criteria"][:2],
                "confidence": 3,
            },
        )
    )
    assert progress_response.status_code == 200
    progressed = progress_response.json()
    assert progressed["completed_count"] == 1
    assert progressed["total_count"] == 6
    assert progressed["sequence"] == 1
    assert progressed["current_activity"]["id"] != current["id"]
    assert progressed["planning_signal_percent"] >= created["planning_signal_percent"]
    assert progressed["verified_readiness_percent"] is None
    assert progressed["claim_state"] == "validation_locked"
    assert progressed["state_token"] != created["state_token"]
    assert progressed["next_review_at"] is not None
    assert len(progressed["evidence_history"]) == 1
    evidence = progressed["evidence_history"][0]
    assert evidence["activity_id"] == current["id"]
    assert evidence["criteria_met"] == current["acceptance_criteria"][:2]
    assert evidence["confidence"] == 3
    assert evidence["planning_signal_delta"] > 0
    assert evidence["evidence_reference"].endswith("/pull/7")


def test_due_review_preempts_available_build_work() -> None:
    now = [datetime(2026, 7, 23, 10, tzinfo=UTC)]
    service = LearningPlanService(
        TEST_SECRET,
        clock=lambda: now[0],
        id_factory=lambda: UUID("00000000-0000-0000-0000-000000000001"),
    )
    created = service.create_plan(PlanRequest(learner_name="Mona"))
    assert created.current_activity is not None
    source = created.current_activity

    progressed = service.complete_activity(
        ProgressRequest(
            state_token=created.state_token,
            activity_id=source.id,
            criteria_met=list(source.acceptance_criteria),
            confidence=0,
            reflection="I completed and checked the bounded deliverable.",
        )
    )
    assert progressed.current_activity is not None
    assert progressed.current_activity.kind == "build"

    now[0] += timedelta(days=2)
    resumed = service.resume(progressed.state_token)
    assert resumed.current_activity is not None
    assert resumed.current_activity.kind == "review"
    assert resumed.current_activity.competency_id == source.competency_id
    assert resumed.current_activity.available_from == progressed.next_review_at


def test_replan_prioritizes_focus_and_preserves_evidence() -> None:
    created_response = asyncio.run(
        request("POST", "/api/v1/plans", {"learner_name": "Nour", "weekly_hours": 8})
    )
    created = created_response.json()
    current = created["current_activity"]
    progressed_response = asyncio.run(
        request(
            "POST",
            "/api/v1/progress",
            {
                "state_token": created["state_token"],
                "activity_id": current["id"],
                "criteria_met": current["acceptance_criteria"],
                "confidence": 2,
                "reflection": "I built the deliverable and recorded the validation evidence.",
            },
        )
    )
    progressed = progressed_response.json()

    replan_response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans/replan",
            {
                "state_token": progressed["state_token"],
                "weekly_hours": 6,
                "focus_competency_ids": ["fastapi", "postgresql"],
            },
        )
    )

    assert replan_response.status_code == 200
    replanned = replan_response.json()
    assert replanned["plan_revision"] == 1
    assert replanned["weekly_hours"] == 6
    assert replanned["focus_competency_ids"] == ["fastapi", "postgresql"]
    assert replanned["evidence_history"] == progressed["evidence_history"]
    assert replanned["active_plan_version"]["trigger"] == "manual_replan"
    assert replanned["active_plan_version"]["delta"]["previous_plan_version_id"] == progressed["active_plan_version"]["plan_version_id"]
    assert replanned["current_activity"]["competency_id"] != "fastapi"
    assert replanned["current_activity"]["generation"] == 1
    focused = [item for item in replanned["priority_competencies"] if item["focused"]]
    assert [item["id"] for item in focused] == ["postgresql", "fastapi"]
    fastapi = next(item for item in focused if item["id"] == "fastapi")
    assert set(fastapi["blocked_by"]) == {"python", "rest"}
    assert replanned["evidence_history"] == progressed["evidence_history"]
    assert replanned["verified_readiness_percent"] is None


def test_invalid_evidence_and_replan_focus_fail_closed() -> None:
    created_response = asyncio.run(request("POST", "/api/v1/plans", {"learner_name": "Ahmed"}))
    created = created_response.json()
    current = created["current_activity"]

    invalid_evidence = asyncio.run(
        request(
            "POST",
            "/api/v1/progress",
            {
                "state_token": created["state_token"],
                "activity_id": current["id"],
                "criteria_met": ["invented criterion"],
                "confidence": 2,
            },
        )
    )
    assert invalid_evidence.status_code == 400
    assert invalid_evidence.json()["detail"]["code"] == "INVALID_EVIDENCE"

    duplicate_evidence = asyncio.run(
        request(
            "POST",
            "/api/v1/progress",
            {
                "state_token": created["state_token"],
                "activity_id": current["id"],
                "criteria_met": [
                    current["acceptance_criteria"][0],
                    current["acceptance_criteria"][0],
                ],
            },
        )
    )
    assert duplicate_evidence.status_code == 400
    assert duplicate_evidence.json()["detail"]["code"] == "INVALID_EVIDENCE"

    invalid_focus = asyncio.run(
        request(
            "POST",
            "/api/v1/plans/replan",
            {
                "state_token": created["state_token"],
                "weekly_hours": 8,
                "focus_competency_ids": ["unknown"],
            },
        )
    )
    assert invalid_focus.status_code == 400
    assert invalid_focus.json()["detail"]["code"] == "INVALID_REPLAN_FOCUS"


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


def test_learner_context_and_revision_change_activity_identity() -> None:
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

    replanned = service.replan(
        ReplanRequest(
            state_token=first.state_token,
            weekly_hours=first.weekly_hours,
            focus_competency_ids=[],
        )
    )
    assert replanned.current_activity is not None
    assert replanned.current_activity.id != first.current_activity.id
    assert replanned.current_activity.generation == 1


def test_production_requires_a_real_signing_secret() -> None:
    with pytest.raises(ValidationError, match="production learner_state_secret"):
        Settings(environment="production")
