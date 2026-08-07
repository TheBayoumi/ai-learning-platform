from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_learning_platform_api.learning.schemas import LearnerState
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    StoredLearnerState,
)


def _state(learner_id: UUID | str) -> LearnerState:
    return LearnerState(
        learner_id=str(learner_id),
        learner_name="Persistence Test Learner",
        target_role="junior-python-backend-engineer",
        weekly_hours=8,
        experience_summary="",
        created_at="2026-07-24T12:00:00+00:00",
        sequence=0,
        mastery={},
        completed_activity_ids=[],
        activities=[],
    )


def test_stored_learner_state_accepts_canonical_owned_snapshot() -> None:
    learner_id = uuid4()
    updated_at = datetime(2026, 7, 24, 12, tzinfo=UTC)

    record = StoredLearnerState(
        account_id="oidc:provider:subject-123",
        learner_id=learner_id,
        version=0,
        state=_state(learner_id),
        updated_at=updated_at,
    )

    assert record.learner_id == learner_id
    assert record.version == 0
    assert record.updated_at == updated_at


@pytest.mark.parametrize(
    "account_id",
    ["", " account", "account id", "a" * 161],
)
def test_stored_learner_state_rejects_noncanonical_account_ids(account_id: str) -> None:
    learner_id = uuid4()

    with pytest.raises(ValueError, match="account_id"):
        StoredLearnerState(
            account_id=account_id,
            learner_id=learner_id,
            version=0,
            state=_state(learner_id),
            updated_at=datetime.now(UTC),
        )


def test_stored_learner_state_rejects_negative_version() -> None:
    learner_id = uuid4()

    with pytest.raises(ValueError, match="version must be non-negative"):
        StoredLearnerState(
            account_id="account-1",
            learner_id=learner_id,
            version=-1,
            state=_state(learner_id),
            updated_at=datetime.now(UTC),
        )


def test_stored_learner_state_rejects_naive_timestamp() -> None:
    learner_id = uuid4()

    with pytest.raises(ValueError, match="updated_at must be timezone-aware"):
        StoredLearnerState(
            account_id="account-1",
            learner_id=learner_id,
            version=0,
            state=_state(learner_id),
            updated_at=datetime(2026, 7, 24, 12),
        )


def test_stored_learner_state_rejects_invalid_state_learner_id() -> None:
    with pytest.raises(ValueError, match="state learner_id must be a UUID"):
        StoredLearnerState(
            account_id="account-1",
            learner_id=uuid4(),
            version=0,
            state=_state("not-a-uuid"),
            updated_at=datetime.now(UTC),
        )


def test_stored_learner_state_rejects_mismatched_learner_id() -> None:
    with pytest.raises(
        ValueError,
        match="state learner_id does not match the aggregate learner_id",
    ):
        StoredLearnerState(
            account_id="account-1",
            learner_id=uuid4(),
            version=0,
            state=_state(uuid4()),
            updated_at=datetime.now(UTC),
        )


def test_learner_state_commit_accepts_atomic_transition_contract() -> None:
    learner_id = uuid4()
    occurred_at = datetime(2026, 7, 24, 12, tzinfo=UTC)

    request = LearnerStateCommit(
        account_id="account-1",
        learner_id=learner_id,
        expected_version=3,
        idempotency_key="progress:command-123",
        event_type="learning.activity.completed.v1",
        state=_state(learner_id),
        occurred_at=occurred_at,
    )

    assert request.expected_version == 3
    assert request.idempotency_key == "progress:command-123"
    assert request.occurred_at == occurred_at


def test_learner_state_commit_allows_create_without_expected_version() -> None:
    learner_id = uuid4()

    request = LearnerStateCommit(
        account_id="account-1",
        learner_id=learner_id,
        expected_version=None,
        idempotency_key="plan:create:command-123",
        event_type="learning.plan.created.v1",
        state=_state(learner_id),
        occurred_at=datetime.now(UTC),
    )

    assert request.expected_version is None


def test_learner_state_commit_rejects_negative_expected_version() -> None:
    learner_id = uuid4()

    with pytest.raises(ValueError, match="expected_version must be non-negative"):
        LearnerStateCommit(
            account_id="account-1",
            learner_id=learner_id,
            expected_version=-1,
            idempotency_key="command-123",
            event_type="learning.plan.updated.v1",
            state=_state(learner_id),
            occurred_at=datetime.now(UTC),
        )


@pytest.mark.parametrize(
    ("field_name", "idempotency_key", "event_type", "expected_message"),
    [
        ("idempotency_key", "", "learning.plan.updated.v1", "idempotency_key"),
        ("idempotency_key", "x" * 161, "learning.plan.updated.v1", "idempotency_key"),
        ("event_type", "command-123", "learning plan updated", "event_type"),
        ("event_type", "command-123", "x" * 121, "event_type"),
    ],
)
def test_learner_state_commit_rejects_invalid_tokens(
    field_name: str,
    idempotency_key: str,
    event_type: str,
    expected_message: str,
) -> None:
    del field_name
    learner_id = uuid4()

    with pytest.raises(ValueError, match=expected_message):
        LearnerStateCommit(
            account_id="account-1",
            learner_id=learner_id,
            expected_version=0,
            idempotency_key=idempotency_key,
            event_type=event_type,
            state=_state(learner_id),
            occurred_at=datetime.now(UTC),
        )


def test_learner_state_commit_rejects_naive_occurred_at() -> None:
    learner_id = uuid4()

    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        LearnerStateCommit(
            account_id="account-1",
            learner_id=learner_id,
            expected_version=0,
            idempotency_key="command-123",
            event_type="learning.plan.updated.v1",
            state=_state(learner_id),
            occurred_at=datetime(2026, 7, 24, 12),
        )
