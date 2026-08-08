"""Deterministic trusted-evidence transitions with no learner-write authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from ai_learning_platform_api.learning.schemas import (
    CompetencyEvidenceState,
    EvidenceEvaluationRecord,
    EvidenceRecordView,
    LearnerState,
    MisconceptionRecord,
    ReviewState,
    TrustedEvidenceVerdict,
)

_MAX_EVALUATIONS = 64
_MAX_MISCONCEPTIONS = 64


class EvidenceTransitionError(ValueError):
    """Base class for deterministic trusted-evidence transition failures."""


class UnknownEvidenceError(EvidenceTransitionError):
    """The trusted verdict references evidence that is not in learner state."""


class EvidenceCompetencyMismatchError(EvidenceTransitionError):
    """The verdict competency does not match the referenced evidence candidate."""


@dataclass(frozen=True, slots=True)
class EvidenceTransitionResult:
    """One deterministic evidence-state transition and whether it changed state."""

    state: LearnerState
    changed: bool


def apply_trusted_verdict(
    *,
    state: LearnerState,
    verdict: TrustedEvidenceVerdict,
    occurred_at: datetime,
) -> EvidenceTransitionResult:
    """Apply one trusted evaluator verdict without changing readiness or planning authority."""
    evidence = _find_evidence(state.evidence_history, verdict.evidence_id)
    if evidence.competency_id != verdict.competency_id:
        raise EvidenceCompetencyMismatchError

    evaluation_id = _evaluation_id(state.learner_id, verdict)
    if any(item.evaluation_id == evaluation_id for item in state.evidence_evaluations):
        return EvidenceTransitionResult(state=state, changed=False)

    evaluation = EvidenceEvaluationRecord(
        evaluation_id=evaluation_id,
        evidence_id=verdict.evidence_id,
        competency_id=verdict.competency_id,
        disposition=verdict.disposition,
        independence=verdict.independence,
        assistance=verdict.assistance,
        reasoning=verdict.reasoning,
        evaluator_id=verdict.evaluator_id,
        evaluator_version=verdict.evaluator_version,
        rubric_version=verdict.rubric_version,
        instance_contract_hash=verdict.instance_contract_hash,
        confidence=verdict.confidence,
        findings=list(verdict.findings),
        misconception_codes=list(verdict.misconception_codes),
        occurred_at=occurred_at.isoformat(),
    )

    current = state.competency_evidence.get(
        verdict.competency_id,
        CompetencyEvidenceState(competency_id=verdict.competency_id),
    )
    competency_state = _competency_state(
        current=current,
        verdict=verdict,
        occurred_at=occurred_at,
    )
    evidence_history = [
        item.model_copy(update={"disposition": verdict.disposition})
        if item.evidence_id == verdict.evidence_id
        else item
        for item in state.evidence_history
    ]
    misconceptions = _misconceptions(
        state=state,
        verdict=verdict,
        occurred_at=occurred_at,
    )
    review_state = dict(state.review_state)
    review_state[verdict.competency_id] = _review_state(
        verdict=verdict,
        occurred_at=occurred_at,
    )

    updated = state.model_copy(
        update={
            "schema_version": 6,
            "evidence_history": evidence_history,
            "evidence_evaluations": [*state.evidence_evaluations, evaluation][-_MAX_EVALUATIONS:],
            "competency_evidence": {
                **state.competency_evidence,
                verdict.competency_id: competency_state,
            },
            "misconceptions": misconceptions[-_MAX_MISCONCEPTIONS:],
            "review_state": review_state,
        }
    )
    return EvidenceTransitionResult(state=updated, changed=True)


def _find_evidence(history: list[EvidenceRecordView], evidence_id: str) -> EvidenceRecordView:
    for item in history:
        if item.evidence_id == evidence_id:
            return item
    raise UnknownEvidenceError


def _competency_state(
    *,
    current: CompetencyEvidenceState,
    verdict: TrustedEvidenceVerdict,
    occurred_at: datetime,
) -> CompetencyEvidenceState:
    accepted = list(current.accepted_evidence_ids)
    disputed = list(current.disputed_evidence_ids)
    status = current.status
    no_hint_verified = current.no_hint_verified
    reasoning_verified = current.reasoning_verified
    assistance = current.assistance

    if verdict.disposition == "accepted":
        accepted = _append_unique(accepted, verdict.evidence_id)
        qualifies_independent = (
            verdict.independence == "independent"
            and verdict.assistance == "none"
            and verdict.reasoning == "verified"
        )
        if qualifies_independent:
            status = "independent"
            no_hint_verified = True
            reasoning_verified = True
            assistance = "none"
        elif status != "independent":
            status = "partial"
            no_hint_verified = no_hint_verified or (
                verdict.independence == "independent" and verdict.assistance == "none"
            )
            reasoning_verified = reasoning_verified or verdict.reasoning == "verified"
            assistance = verdict.assistance
    elif verdict.disposition == "disputed":
        disputed = _append_unique(disputed, verdict.evidence_id)

    return current.model_copy(
        update={
            "status": status,
            "accepted_evidence_ids": accepted,
            "disputed_evidence_ids": disputed,
            "last_evaluated_at": occurred_at.isoformat(),
            "no_hint_verified": no_hint_verified,
            "reasoning_verified": reasoning_verified,
            "assistance": assistance,
        }
    )


def _misconceptions(
    *,
    state: LearnerState,
    verdict: TrustedEvidenceVerdict,
    occurred_at: datetime,
) -> list[MisconceptionRecord]:
    existing = list(state.misconceptions)
    known = {item.misconception_id for item in existing}
    for code in verdict.misconception_codes:
        misconception_id = _hash_id(
            "misconception",
            state.learner_id,
            verdict.competency_id,
            verdict.evidence_id,
            code,
        )
        if misconception_id in known:
            continue
        existing.append(
            MisconceptionRecord(
                misconception_id=misconception_id,
                competency_id=verdict.competency_id,
                code=code,
                status="active",
                evidence_id=verdict.evidence_id,
                observed_at=occurred_at.isoformat(),
            )
        )
        known.add(misconception_id)
    return existing


def _review_state(*, verdict: TrustedEvidenceVerdict, occurred_at: datetime) -> ReviewState:
    qualifies_independent = (
        verdict.disposition == "accepted"
        and verdict.independence == "independent"
        and verdict.assistance == "none"
        and verdict.reasoning == "verified"
    )
    if qualifies_independent:
        return ReviewState(
            competency_id=verdict.competency_id,
            due_at=(occurred_at + timedelta(days=7)).isoformat(),
            stage="retention_candidate",
            source_evidence_id=verdict.evidence_id,
            reason=(
                "Independent evidence qualified for a later retention probe; this is not itself "
                "retention proof."
            ),
        )
    return ReviewState(
        competency_id=verdict.competency_id,
        due_at=(occurred_at + timedelta(days=3)).isoformat(),
        stage="evidence_follow_up",
        source_evidence_id=verdict.evidence_id,
        reason="Evidence requires follow-up before any stronger competency claim is possible.",
    )


def _evaluation_id(learner_id: str, verdict: TrustedEvidenceVerdict) -> str:
    payload = json.dumps(
        verdict.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _hash_id("evaluation", learner_id, payload)


def _hash_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _append_unique(values: list[str], value: str) -> list[str]:
    return values if value in values else [*values, value]
