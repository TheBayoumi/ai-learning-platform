from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_learning_platform_api.learning.schemas import LearnerState
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.persistence.schemas import (
    AccountDataExportView,
    LearnerDataExportView,
    LearnerOperationalAuditView,
)
from ai_learning_platform_api.transport.http.privacy import create_privacy_router

_ACCOUNT = "99999999-9999-4999-8999-999999999999"


def _export() -> AccountDataExportView:
    state = LearnerState(
        storage_mode="durable",
        learner_id="90000000-0000-4000-8000-000000000099",
        learner_name="Privacy Export Learner",
        target_role="junior-python-backend-engineer",
        weekly_hours=4,
        experience_summary="",
        created_at=datetime(2026, 8, 8, tzinfo=UTC).isoformat(),
        sequence=0,
        planning_signal={},
        mastery={},
        completed_activity_ids=[],
        activities=[],
    )
    return AccountDataExportView(
        generated_at=datetime(2026, 8, 8, tzinfo=UTC).isoformat(),
        learners=[
            LearnerDataExportView(
                learner_id=UUID(state.learner_id),
                aggregate_version=0,
                updated_at=datetime(2026, 8, 8, tzinfo=UTC).isoformat(),
                state=state,
                audit=LearnerOperationalAuditView(
                    raw_state_bytes=512,
                    evidence_records=0,
                    evaluation_records=0,
                    retained_plan_versions=0,
                    verification_probes=0,
                    work_provenance_records=0,
                    active_task_exposures=0,
                    replay_verified=True,
                    claim_integrity_verified=True,
                    within_resource_bounds=True,
                ),
            )
        ],
        redactions=["server_secrets", "provider_credentials", "account_cookie"],
        retention_notes=["unlinkable_task_collision_fingerprints"],
    )


def _client(export_mode: str = "ok") -> TestClient:
    async def delete_account(account_id: str) -> bool:
        return account_id == _ACCOUNT

    async def export_account(account_id: str) -> AccountDataExportView:
        assert account_id == _ACCOUNT
        if export_mode == "missing":
            raise LearnerStateNotFoundError
        if export_mode == "unavailable":
            raise PersistenceUnavailableError
        return _export()

    app = FastAPI()
    app.include_router(create_privacy_router(delete_account, export_account))
    return TestClient(app)


def test_same_origin_account_export_returns_redacted_replay_verified_data() -> None:
    response = _client().get(
        "/api/v1/account/export",
        headers={"X-Platform-Account-Id": _ACCOUNT},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["learners"][0]["audit"]["replay_verified"] is True
    assert _ACCOUNT not in response.text
    assert "server_secrets" in payload["redactions"]


def test_export_maps_missing_and_unavailable_storage_fail_closed() -> None:
    missing = _client("missing").get(
        "/api/v1/account/export",
        headers={"X-Platform-Account-Id": _ACCOUNT},
    )
    unavailable = _client("unavailable").get(
        "/api/v1/account/export",
        headers={"X-Platform-Account-Id": _ACCOUNT},
    )

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ACCOUNT_DATA_NOT_FOUND"
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "PERSISTENCE_UNAVAILABLE"


def test_invalid_account_context_is_rejected_before_export() -> None:
    response = _client().get(
        "/api/v1/account/export",
        headers={"X-Platform-Account-Id": "not-a-uuid"},
    )
    assert response.status_code in {400, 422}
