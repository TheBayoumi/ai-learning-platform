from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.provenance import (
    InvalidCheckpointChainError,
    UnknownWorkEvidenceError,
    WorkChallengeBindingError,
    WorkProvenanceAlreadyEvaluatedError,
    WorkProvenanceBindingError,
    apply_work_provenance_verdict,
    capture_work_provenance,
    issue_work_challenges,
    project_work_provenance,
)
from ai_learning_platform_api.learning.schemas import (
    ArtifactCheckpointView,
    EvidenceRecordView,
    LearnerState,
    PlanRequest,
    ProgressRequest,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceState,
    WorkProvenanceSubmission,
)

_SECRET = "g07-provenance-edge-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _service() -> LearningPlanService:
    return LearningPlanService(
        _SECRET,
        clock=lambda: _NOW,
        id_factory=lambda: UUID("71717171-7171-4717-8717-717171717171"),
    )


def _recorded_state() -> tuple[LearningPlanService, LearnerState, EvidenceRecordView]:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Edge Provenance", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection=(
                "I recorded the implementation decisions, trade-offs, and verification steps "
                "for independent provenance review."
            ),
            evidence_reference="repo://g07-edge",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    state = service._codec.decode(progressed.state_token)
    return service, state, progressed.evidence_history[-1]


def _issued_state() -> tuple[LearningPlanService, LearnerState, EvidenceRecordView]:
    service, state, evidence = _recorded_state()
    issued = issue_work_challenges(state=state, evidence_id=evidence.evidence_id, occurred_at=_NOW)
    assert issued.changed is True
    return service, issued.state, evidence


def _checkpoint(
    identifier: str,
    artifact_hash: str,
    *,
    parent: str = "",
    created_at: str | None = None,
) -> ArtifactCheckpointView:
    return ArtifactCheckpointView(
        checkpoint_id=identifier,
        artifact_sha256=artifact_hash,
        parent_checkpoint_id=parent,
        created_at=created_at or _NOW.isoformat(),
        change_summary="Recorded a material implementation change for provenance review.",
        toolchain=["python", "git"],
        assistance="none",
    )


def _submission(
    state: LearnerState,
    evidence: EvidenceRecordView,
    *,
    checkpoints: list[ArtifactCheckpointView] | None = None,
    source_attribution: str = "Self-authored; project documentation consulted.",
    modification_reference: str = "repo://edge/modification",
    debugging_reference: str = "repo://edge/debugging",
    defense: str = (
        "I selected deterministic ownership to preserve replay and isolation. I rejected a "
        "provider-owned shortcut because it could silently alter evidence authority, and I "
        "verified the hidden modification and debugging correction with focused tests."
    ),
) -> WorkProvenanceSubmission:
    record = state.work_provenance[evidence.evidence_id]
    challenges = {item.kind: item.challenge_id for item in record.challenges}
    values = checkpoints or [
        _checkpoint("edge-cp-1", "1" * 64),
        _checkpoint(
            "edge-cp-2",
            "2" * 64,
            parent="edge-cp-1",
            created_at=(_NOW + timedelta(hours=1)).isoformat(),
        ),
    ]
    return WorkProvenanceSubmission(
        evidence_id=evidence.evidence_id,
        artifact_id="edge-artifact",
        final_artifact_sha256=values[-1].artifact_sha256,
        checkpoints=values,
        assistance_disclosure="none",
        source_attribution=source_attribution,
        modification_challenge_id=challenges["modification"],
        modification_evidence_reference=modification_reference,
        debugging_challenge_id=challenges["debugging"],
        debugging_evidence_reference=debugging_reference,
        defense_challenge_id=challenges["defense"],
        defense_response=defense,
    )


def _verdict(
    evidence: EvidenceRecordView, *, artifact_id: str = "edge-artifact"
) -> TrustedWorkProvenanceVerdict:
    return TrustedWorkProvenanceVerdict(
        evidence_id=evidence.evidence_id,
        artifact_id=artifact_id,
        disposition="accepted",
        authorship_verified=True,
        modification_verified=True,
        debugging_verified=True,
        defense_verified=True,
        evaluator_id="g07-edge-reviewer",
        evaluator_version="v1",
        confidence=96,
    )


def test_unknown_evidence_and_duplicate_challenge_issuance_are_fail_closed_or_idempotent() -> None:
    _, state, evidence = _recorded_state()
    with pytest.raises(UnknownWorkEvidenceError):
        issue_work_challenges(state=state, evidence_id="missing-evidence", occurred_at=_NOW)

    first = issue_work_challenges(state=state, evidence_id=evidence.evidence_id, occurred_at=_NOW)
    second = issue_work_challenges(
        state=first.state,
        evidence_id=evidence.evidence_id,
        occurred_at=_NOW + timedelta(minutes=1),
    )
    assert first.changed is True
    assert second.changed is False
    assert second.state == first.state


def test_capture_requires_a_server_issued_challenge_and_cannot_be_rewritten() -> None:
    _, raw_state, evidence = _recorded_state()
    fake_state = raw_state.model_copy(
        update={
            "work_provenance": {
                evidence.evidence_id: WorkProvenanceState(
                    evidence_id=evidence.evidence_id,
                    status="captured",
                    artifact_id="already-captured",
                    captured_at=_NOW.isoformat(),
                )
            }
        }
    )
    with pytest.raises(WorkChallengeBindingError):
        capture_work_provenance(
            state=raw_state,
            submission=WorkProvenanceSubmission(
                evidence_id=evidence.evidence_id,
                artifact_id="edge-artifact",
                final_artifact_sha256="1" * 64,
                checkpoints=[_checkpoint("edge-cp-1", "1" * 64)],
                modification_challenge_id="work-modification-missing",
                debugging_challenge_id="work-debugging-missing",
                defense_challenge_id="work-defense-missing",
            ),
            occurred_at=_NOW,
        )
    with pytest.raises(WorkChallengeBindingError):
        capture_work_provenance(
            state=fake_state,
            submission=WorkProvenanceSubmission(
                evidence_id=evidence.evidence_id,
                artifact_id="edge-artifact",
                final_artifact_sha256="1" * 64,
                checkpoints=[_checkpoint("edge-cp-1", "1" * 64)],
                modification_challenge_id="work-modification-missing",
                debugging_challenge_id="work-debugging-missing",
                defense_challenge_id="work-defense-missing",
            ),
            occurred_at=_NOW,
        )


def test_second_capture_of_an_issued_artifact_is_rejected() -> None:
    _, issued, evidence = _issued_state()
    submission = _submission(issued, evidence)
    captured = capture_work_provenance(state=issued, submission=submission, occurred_at=_NOW)
    with pytest.raises(WorkChallengeBindingError):
        capture_work_provenance(
            state=captured.state,
            submission=submission,
            occurred_at=_NOW + timedelta(minutes=1),
        )


def test_review_requires_captured_record_and_exact_artifact_binding() -> None:
    _, issued, evidence = _issued_state()
    with pytest.raises(WorkProvenanceBindingError):
        apply_work_provenance_verdict(
            state=issued,
            verdict=_verdict(evidence),
            occurred_at=_NOW,
        )
    captured = capture_work_provenance(
        state=issued,
        submission=_submission(issued, evidence),
        occurred_at=_NOW,
    )
    with pytest.raises(WorkProvenanceBindingError):
        apply_work_provenance_verdict(
            state=captured.state,
            verdict=_verdict(evidence, artifact_id="wrong-artifact"),
            occurred_at=_NOW,
        )


def test_reviewed_record_is_idempotent_only_for_the_exact_same_verdict() -> None:
    _, issued, evidence = _issued_state()
    captured = capture_work_provenance(
        state=issued,
        submission=_submission(issued, evidence),
        occurred_at=_NOW,
    )
    verdict = _verdict(evidence)
    first = apply_work_provenance_verdict(
        state=captured.state,
        verdict=verdict,
        occurred_at=_NOW,
    )
    duplicate = apply_work_provenance_verdict(
        state=first.state,
        verdict=verdict,
        occurred_at=_NOW + timedelta(minutes=2),
    )
    assert duplicate.changed is False
    with pytest.raises(WorkProvenanceAlreadyEvaluatedError):
        apply_work_provenance_verdict(
            state=first.state,
            verdict=verdict.model_copy(update={"confidence": 95}),
            occurred_at=_NOW + timedelta(minutes=3),
        )


@pytest.mark.parametrize(
    "checkpoints",
    [
        [
            _checkpoint("duplicate", "1" * 64),
            _checkpoint(
                "duplicate",
                "2" * 64,
                parent="duplicate",
                created_at=(_NOW + timedelta(hours=1)).isoformat(),
            ),
        ],
        [
            _checkpoint("root-parent", "1" * 64, parent="unexpected-parent"),
        ],
        [
            _checkpoint("bad-time", "1" * 64, created_at="not-a-date-value"),
        ],
        [
            _checkpoint("naive-time", "1" * 64, created_at="2026-08-08T12:00:00"),
        ],
        [
            _checkpoint("later", "1" * 64, created_at=(_NOW + timedelta(hours=2)).isoformat()),
            _checkpoint(
                "earlier",
                "2" * 64,
                parent="later",
                created_at=(_NOW + timedelta(hours=1)).isoformat(),
            ),
        ],
    ],
)
def test_malformed_checkpoint_history_is_rejected(
    checkpoints: list[ArtifactCheckpointView],
) -> None:
    _, issued, evidence = _issued_state()
    with pytest.raises(InvalidCheckpointChainError):
        capture_work_provenance(
            state=issued,
            submission=_submission(issued, evidence, checkpoints=checkpoints),
            occurred_at=_NOW,
        )


def test_incomplete_capture_remains_reviewed_but_blocked() -> None:
    _, issued, evidence = _issued_state()
    one_checkpoint = [_checkpoint("single-cp", "3" * 64)]
    captured = capture_work_provenance(
        state=issued,
        submission=_submission(
            issued,
            evidence,
            checkpoints=one_checkpoint,
            source_attribution="",
            modification_reference="",
            debugging_reference="",
            defense="too short",
        ),
        occurred_at=_NOW,
    )
    reviewed = apply_work_provenance_verdict(
        state=captured.state,
        verdict=_verdict(evidence),
        occurred_at=_NOW,
    )
    record = reviewed.state.work_provenance[evidence.evidence_id]
    assert record.status == "reviewed_blocked"
    assert record.eligible_for_readiness is False
    assert "insufficient_checkpoint_history" in record.issues
    assert "missing_source_attribution" in record.issues
    assert "missing_modification_evidence" in record.issues
    assert "missing_debugging_evidence" in record.issues
    assert "insufficient_defense_response" in record.issues


def test_untrusted_source_remains_blocked_even_with_perfect_work_review() -> None:
    _, issued, evidence = _issued_state()
    issued = issued.model_copy(
        update={
            "evidence_history": [
                item.model_copy(update={"source_high_stakes_eligible": False})
                if item.evidence_id == evidence.evidence_id
                else item
                for item in issued.evidence_history
            ]
        }
    )
    captured = capture_work_provenance(
        state=issued,
        submission=_submission(issued, evidence),
        occurred_at=_NOW,
    )
    reviewed = apply_work_provenance_verdict(
        state=captured.state,
        verdict=_verdict(evidence),
        occurred_at=_NOW,
    )
    record = reviewed.state.work_provenance[evidence.evidence_id]
    assert "source_not_high_stakes_eligible" in record.issues
    assert record.eligible_for_readiness is False


def test_projection_is_empty_for_legacy_state_and_sorted_for_captured_records() -> None:
    _, state, evidence = _recorded_state()
    assert project_work_provenance(state) == []
    first = WorkProvenanceState(
        evidence_id=evidence.evidence_id,
        status="challenge_issued",
        captured_at=(_NOW + timedelta(hours=2)).isoformat(),
    )
    second = WorkProvenanceState(
        evidence_id="evidence-earlier",
        status="challenge_issued",
        captured_at=_NOW.isoformat(),
    )
    projected = project_work_provenance(
        state.model_copy(
            update={
                "work_provenance": {
                    first.evidence_id: first,
                    second.evidence_id: second,
                }
            }
        )
    )
    assert [item.evidence_id for item in projected] == [second.evidence_id, first.evidence_id]
