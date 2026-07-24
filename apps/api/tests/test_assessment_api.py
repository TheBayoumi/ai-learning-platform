from __future__ import annotations

import asyncio
import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import httpx
from pydantic import SecretStr

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.learning.assessment import InvalidAssessmentAttemptError
from ai_learning_platform_api.learning.schemas import (
    AssessmentAnswer,
    AssessmentStartRequest,
    AssessmentSubmitRequest,
    PlanRequest,
    ReplanRequest,
)
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.settings import Settings

TEST_SECRET = "test-assessment-secret-with-at-least-thirty-two-bytes"
CORRECT_OPTIONS = {
    "python-mutable-default": "b",
    "fastapi-domain-boundary": "c",
    "postgresql-integrity": "a",
    "rest-idempotency": "b",
    "testing-observable-behavior": "a",
    "git-shared-history": "c",
    "docker-runtime-hardening": "b",
    "ci-supply-chain": "b",
    "debugging-correlation": "a",
    "communication-facts-hypotheses": "b",
}


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


def _create_plan() -> dict[str, Any]:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/plans",
            {
                "learner_name": "Calibration Learner",
                "weekly_hours": 8,
                "ratings": [],
            },
        )
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def _start(plan: dict[str, Any], count: int = 4) -> dict[str, Any]:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/start",
            {"state_token": plan["state_token"], "question_count": count},
        )
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _answers(attempt: dict[str, Any], *, correct: bool) -> list[dict[str, str]]:
    questions = attempt["questions"]
    assert isinstance(questions, list)
    result: list[dict[str, str]] = []
    for question in questions:
        assert isinstance(question, dict)
        question_id = str(question["id"])
        options = question["options"]
        assert isinstance(options, list)
        option_ids = [str(option["id"]) for option in options if isinstance(option, dict)]
        correct_id = CORRECT_OPTIONS[question_id]
        selected = (
            correct_id if correct else next(item for item in option_ids if item != correct_id)
        )
        result.append({"question_id": question_id, "option_id": selected})
    return result


def test_start_hides_answers_and_selects_priority_competencies() -> None:
    plan = _create_plan()
    attempt = _start(plan)

    assert attempt["bank_version"] == "2026.07-calibration-1"
    questions = attempt["questions"]
    assert isinstance(questions, list)
    assert len(questions) == 4
    competency_ids = [question["competency_id"] for question in questions]
    assert competency_ids == ["python", "fastapi", "postgresql", "testing"]

    rendered = json.dumps(attempt, sort_keys=True)
    assert "correct_option" not in rendered
    assert "explanation" not in rendered

    encoded_payload = str(attempt["attempt_token"]).split(".", maxsplit=1)[0]
    padding = "=" * (-len(encoded_payload) % 4)
    token_payload = json.loads(base64.urlsafe_b64decode(encoded_payload + padding))
    assert set(token_payload) == {
        "attempt_id",
        "bank_version",
        "expires_at",
        "issued_at",
        "learner_id",
        "question_ids",
        "role_id",
        "schema_version",
        "state_sequence",
    }
    assert "correct" not in json.dumps(token_payload)


def test_submit_all_correct_calibrates_and_replans() -> None:
    plan = _create_plan()
    attempt = _start(plan)
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/submit",
            {
                "state_token": plan["state_token"],
                "attempt_token": attempt["attempt_token"],
                "answers": _answers(attempt, correct=True),
            },
        )
    )

    assert response.status_code == 200
    result = response.json()
    assert result["score_percent"] == 100
    assert result["correct_count"] == 4
    assert result["total_count"] == 4
    assert all(item["correct"] for item in result["feedback"])
    assert all(item["explanation"] for item in result["feedback"])

    updated = result["plan"]
    assert updated["assessment_coverage_percent"] == 40
    assert updated["evidence_readiness_percent"] == 0
    assert updated["readiness_percent"] > 0
    assert updated["plan_revision"] == 1
    assert updated["sequence"] == 1
    assert len(updated["assessment_history"]) == 1
    assessment_record = updated["assessment_history"][0]
    assert assessment_record["score_percent"] == 100
    assert assessment_record["competency_scores"] == {
        "python": 100,
        "fastapi": 100,
        "postgresql": 100,
        "testing": 100,
    }
    assert updated["current_activity"]["generation"] == 1
    assessed_priorities = {
        item["id"]: item["assessment_percent"]
        for item in updated["priority_competencies"]
        if item["assessment_percent"] is not None
    }
    assert set(assessed_priorities).issubset(assessment_record["competency_scores"])
    assert all(score == 100 for score in assessed_priorities.values())


def test_wrong_answers_do_not_overstate_calibration() -> None:
    plan = _create_plan()
    attempt = _start(plan, count=2)
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/submit",
            {
                "state_token": plan["state_token"],
                "attempt_token": attempt["attempt_token"],
                "answers": _answers(attempt, correct=False),
            },
        )
    )

    assert response.status_code == 200
    result = response.json()
    assert result["score_percent"] == 0
    assert not any(item["correct"] for item in result["feedback"])
    assert result["plan"]["readiness_percent"] == 0
    assert result["plan"]["assessment_coverage_percent"] == 20


def test_missing_duplicate_and_invalid_options_fail_closed() -> None:
    plan = _create_plan()
    attempt = _start(plan, count=2)
    answers = _answers(attempt, correct=True)

    missing = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/submit",
            {
                "state_token": plan["state_token"],
                "attempt_token": attempt["attempt_token"],
                "answers": answers[:1],
            },
        )
    )
    assert missing.status_code == 400
    assert missing.json()["detail"]["code"] == "INVALID_ASSESSMENT_ANSWER"

    duplicate = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/submit",
            {
                "state_token": plan["state_token"],
                "attempt_token": attempt["attempt_token"],
                "answers": [answers[0], answers[0]],
            },
        )
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "INVALID_ASSESSMENT_ANSWER"

    invalid = [*answers]
    invalid[0] = {**invalid[0], "option_id": "unavailable"}
    unavailable = asyncio.run(
        request(
            "POST",
            "/api/v1/assessments/submit",
            {
                "state_token": plan["state_token"],
                "attempt_token": attempt["attempt_token"],
                "answers": invalid,
            },
        )
    )
    assert unavailable.status_code == 400
    assert unavailable.json()["detail"]["code"] == "INVALID_ASSESSMENT_ANSWER"


def test_attempt_expires_and_is_bound_to_state_sequence() -> None:
    now = [datetime(2026, 7, 24, 10, tzinfo=UTC)]
    service = LearningPlanService(
        TEST_SECRET,
        clock=lambda: now[0],
        id_factory=lambda: UUID("00000000-0000-0000-0000-000000000001"),
    )
    plan = service.create_plan(PlanRequest(learner_name="Mona"))
    attempt = service.start_assessment(
        AssessmentStartRequest(state_token=plan.state_token, question_count=2)
    )
    answers = [
        AssessmentAnswer(
            question_id=question.id,
            option_id=CORRECT_OPTIONS[question.id],
        )
        for question in attempt.questions
    ]

    now[0] += timedelta(minutes=31)
    try:
        service.submit_assessment(
            AssessmentSubmitRequest(
                state_token=plan.state_token,
                attempt_token=attempt.attempt_token,
                answers=answers,
            )
        )
    except InvalidAssessmentAttemptError:
        pass
    else:
        raise AssertionError("expired attempt was accepted")

    now[0] -= timedelta(minutes=31)
    replanned = service.replan(
        ReplanRequest(
            state_token=plan.state_token,
            weekly_hours=8,
            focus_competency_ids=[],
        )
    )
    try:
        service.submit_assessment(
            AssessmentSubmitRequest(
                state_token=replanned.state_token,
                attempt_token=attempt.attempt_token,
                answers=answers,
            )
        )
    except InvalidAssessmentAttemptError:
        pass
    else:
        raise AssertionError("attempt bound to an older state sequence was accepted")
