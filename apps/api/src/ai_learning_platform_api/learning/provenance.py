"""Deterministic artifact provenance, modification/debugging, and defense transitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from ai_learning_platform_api.learning.schemas import (
    ArtifactCheckpointView,
    LearnerState,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceState,
    WorkProvenanceSubmission,
    WorkVerificationChallengeView,
)

_MAX_PROVENANCE_RECORDS = 32


class WorkProvenanceError(ValueError):
    """Base class for fail-closed work provenance errors."""


class UnknownWorkEvidenceError(WorkProvenanceError):
    """The work command references no retained evidence candidate."""


class WorkChallengeBindingError(WorkProvenanceError):
    """The submitted work does not match its server-issued challenges."""


class InvalidCheckpointChainError(WorkProvenanceError):
    """Artifact checkpoints are malformed, reordered, or inconsistent."""


class WorkProvenanceBindingError(WorkProvenanceError):
    """A trusted verdict does not match the captured artifact provenance."""


class WorkProvenanceAlreadyEvaluatedError(WorkProvenanceError):
    """A completed provenance evaluation cannot be overwritten."""


@dataclass(frozen=True, slots=True)
class WorkProvenanceTransitionResult:
    state: LearnerState
    changed: bool


def issue_work_challenges(
    *,
    state: LearnerState,
    evidence_id: str,
    occurred_at: datetime,
) -> WorkProvenanceTransitionResult:
    """Issue post-artifact verification challenges without granting any evidence authority."""
    evidence = _find_evidence(state, evidence_id)
    current = state.work_provenance.get(evidence_id)
    if current is not None:
        return WorkProvenanceTransitionResult(state=state, changed=False)

    challenges = [
        _challenge(
            state=state,
            evidence_id=evidence_id,
            kind="modification",
            prompt=(
                "Change one material implementation choice while preserving the original "
                f"{evidence.title!r} acceptance contract. Record the before/after behavior."
            ),
            occurred_at=occurred_at,
        ),
        _challenge(
            state=state,
            evidence_id=evidence_id,
            kind="debugging",
            prompt=(
                "Diagnose and repair a controlled failure in the submitted work. Explain the "
                "failure mechanism and the smallest defensible correction without answer-level help."
            ),
            occurred_at=occurred_at,
        ),
        _challenge(
            state=state,
            evidence_id=evidence_id,
            kind="defense",
            prompt=(
                "Defend the major design choices, trade-offs, rejected alternatives, and likely "
                "failure modes of the submitted work in your own reasoning."
            ),
            occurred_at=occurred_at,
        ),
    ]
    record = WorkProvenanceState(
        evidence_id=evidence_id,
        artifact_id="",
        status="challenge_issued",
        challenges=challenges,
        captured_at=occurred_at.isoformat(),
    )
    return WorkProvenanceTransitionResult(
        state=state.model_copy(
            update={
                "work_provenance": {
                    **state.work_provenance,
                    evidence_id: record,
                }
            }
        ),
        changed=True,
    )


def capture_work_provenance(
    *,
    state: LearnerState,
    submission: WorkProvenanceSubmission,
    occurred_at: datetime,
) -> WorkProvenanceTransitionResult:
    """Capture immutable learner-declared work history; capture alone never grants readiness."""
    evidence = _find_evidence(state, submission.evidence_id)
    current = state.work_provenance.get(submission.evidence_id)
    if current is None or current.status != "challenge_issued":
        raise WorkChallengeBindingError
    if current.artifact_id:
        raise WorkProvenanceAlreadyEvaluatedError
    _validate_challenges(current, submission)
    _validate_checkpoint_chain(submission.checkpoints, submission.final_artifact_sha256)

    issues = _capture_issues(submission)
    record = current.model_copy(
        update={
            "artifact_id": submission.artifact_id,
            "status": "captured",
            "final_artifact_sha256": submission.final_artifact_sha256,
            "checkpoints": list(submission.checkpoints),
            "assistance_disclosure": submission.assistance_disclosure,
            "source_attribution": submission.source_attribution.strip(),
            "modification_evidence_reference": submission.modification_evidence_reference.strip(),
            "debugging_evidence_reference": submission.debugging_evidence_reference.strip(),
            "defense_response": submission.defense_response.strip(),
            "source_high_stakes_eligible": evidence.source_high_stakes_eligible,
            "captured_at": occurred_at.isoformat(),
            "issues": issues,
            "eligible_for_readiness": False,
        }
    )
    return WorkProvenanceTransitionResult(
        state=state.model_copy(
            update={
                "work_provenance": {
                    **state.work_provenance,
                    submission.evidence_id: record,
                }
            }
        ),
        changed=True,
    )


def apply_work_provenance_verdict(
    *,
    state: LearnerState,
    verdict: TrustedWorkProvenanceVerdict,
    occurred_at: datetime,
) -> WorkProvenanceTransitionResult:
    """Apply a trusted work verdict without changing competency qualification or readiness itself."""
    evidence = _find_evidence(state, verdict.evidence_id)
    current = state.work_provenance.get(verdict.evidence_id)
    if current is None or current.status == "challenge_issued":
        raise WorkProvenanceBindingError
    if current.artifact_id != verdict.artifact_id:
        raise WorkProvenanceBindingError

    evaluation_id = _evaluation_id(verdict)
    if current.evaluation_id:
        if current.evaluation_id == evaluation_id:
            return WorkProvenanceTransitionResult(state=state, changed=False)
        raise WorkProvenanceAlreadyEvaluatedError

    checkpoint_issues = _checkpoint_issues(current.checkpoints, current.final_artifact_sha256)
    issues = [*current.issues, *checkpoint_issues]
    if not evidence.source_high_stakes_eligible:
        issues.append("source_not_high_stakes_eligible")
    if current.assistance_disclosure == "answer_level" or any(
        item.assistance == "answer_level" for item in current.checkpoints
    ):
        issues.append("answer_level_assistance")
    if len(current.checkpoints) < 2:
        issues.append("insufficient_checkpoint_history")
    if not current.source_attribution.strip():
        issues.append("missing_source_attribution")

    trusted_requirements = {
        "authorship_verified": verdict.authorship_verified,
        "modification_verified": verdict.modification_verified,
        "debugging_verified": verdict.debugging_verified,
        "defense_verified": verdict.defense_verified,
    }
    for code, passed in trusted_requirements.items():
        if not passed:
            issues.append(code.replace("_verified", "_unverified"))

    accepted = verdict.disposition == "accepted"
    eligible = accepted and not issues and all(trusted_requirements.values())
    status = "verified" if eligible else verdict.disposition
    record = current.model_copy(
        update={
            "status": status,
            "authorship_verified": verdict.authorship_verified,
            "modification_verified": verdict.modification_verified,
            "debugging_verified": verdict.debugging_verified,
            "defense_verified": verdict.defense_verified,
            "evaluator_id": verdict.evaluator_id,
            "evaluator_version": verdict.evaluator_version,
            "evaluation_id": evaluation_id,
            "evaluated_at": occurred_at.isoformat(),
            "issues": _dedupe(issues),
            "eligible_for_readiness": eligible,
        }
    )
    work_provenance = dict(state.work_provenance)
    work_provenance[verdict.evidence_id] = record
    if len(work_provenance) > _MAX_PROVENANCE_RECORDS:
        ordered = sorted(
            work_provenance.values(),
            key=lambda item: (item.captured_at, item.evidence_id),
        )[-_MAX_PROVENANCE_RECORDS:]
        work_provenance = {item.evidence_id: item for item in ordered}
    return WorkProvenanceTransitionResult(
        state=state.model_copy(update={"work_provenance": work_provenance}),
        changed=True,
    )


def project_work_provenance(state: LearnerState) -> list[WorkProvenanceState]:
    """Return deterministic provenance records without synthesizing missing legacy history."""
    return sorted(
        state.work_provenance.values(),
        key=lambda item: (item.captured_at, item.evidence_id),
    )


def _find_evidence(state: LearnerState, evidence_id: str):
    for item in state.evidence_history:
        if item.evidence_id == evidence_id:
            return item
    raise UnknownWorkEvidenceError


def _challenge(
    *,
    state: LearnerState,
    evidence_id: str,
    kind: str,
    prompt: str,
    occurred_at: datetime,
) -> WorkVerificationChallengeView:
    digest = hashlib.sha256(
        f"{state.learner_id}|{evidence_id}|{kind}|{state.active_plan_version_id}".encode("utf-8")
    ).hexdigest()[:24]
    return WorkVerificationChallengeView(
        challenge_id=f"work-{kind}-{digest}",
        evidence_id=evidence_id,
        kind=kind,
        prompt=prompt,
        issued_at=occurred_at.isoformat(),
    )


def _validate_challenges(
    current: WorkProvenanceState,
    submission: WorkProvenanceSubmission,
) -> None:
    expected = {item.kind: item.challenge_id for item in current.challenges}
    supplied = {
        "modification": submission.modification_challenge_id,
        "debugging": submission.debugging_challenge_id,
        "defense": submission.defense_challenge_id,
    }
    if expected != supplied:
        raise WorkChallengeBindingError


def _validate_checkpoint_chain(
    checkpoints: list[ArtifactCheckpointView],
    final_artifact_sha256: str,
) -> None:
    issues = _checkpoint_issues(checkpoints, final_artifact_sha256)
    if issues:
        raise InvalidCheckpointChainError(",".join(issues))


def _checkpoint_issues(
    checkpoints: list[ArtifactCheckpointView],
    final_artifact_sha256: str,
) -> list[str]:
    if not checkpoints:
        return ["missing_checkpoints"]
    issues: list[str] = []
    seen: set[str] = set()
    previous_id = ""
    previous_time: datetime | None = None
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint.checkpoint_id in seen:
            issues.append("duplicate_checkpoint_id")
        seen.add(checkpoint.checkpoint_id)
        if index == 0:
            if checkpoint.parent_checkpoint_id:
                issues.append("invalid_root_checkpoint_parent")
        elif checkpoint.parent_checkpoint_id != previous_id:
            issues.append("broken_checkpoint_parent_chain")
        try:
            current_time = datetime.fromisoformat(checkpoint.created_at)
        except ValueError:
            issues.append("invalid_checkpoint_timestamp")
            current_time = None
        if current_time is not None:
            if current_time.tzinfo is None:
                issues.append("naive_checkpoint_timestamp")
            if previous_time is not None and current_time <= previous_time:
                issues.append("non_monotonic_checkpoint_timestamp")
            previous_time = current_time
        previous_id = checkpoint.checkpoint_id
    if checkpoints[-1].artifact_sha256 != final_artifact_sha256:
        issues.append("final_artifact_hash_mismatch")
    return _dedupe(issues)


def _capture_issues(submission: WorkProvenanceSubmission) -> list[str]:
    issues: list[str] = []
    if not submission.source_attribution.strip():
        issues.append("missing_source_attribution")
    if submission.assistance_disclosure == "answer_level":
        issues.append("answer_level_assistance")
    if any(item.assistance == "answer_level" for item in submission.checkpoints):
        issues.append("answer_level_assistance")
    if not submission.modification_evidence_reference.strip():
        issues.append("missing_modification_evidence")
    if not submission.debugging_evidence_reference.strip():
        issues.append("missing_debugging_evidence")
    if len(submission.defense_response.strip()) < 80:
        issues.append("insufficient_defense_response")
    return _dedupe(issues)


def _evaluation_id(verdict: TrustedWorkProvenanceVerdict) -> str:
    payload = json.dumps(
        verdict.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "work-eval-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
