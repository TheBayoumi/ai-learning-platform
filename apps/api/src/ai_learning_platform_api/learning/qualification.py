"""Deterministic independent, retention, and transfer qualification transitions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from ai_learning_platform_api.learning.schemas import (
    CompetencyQualificationState,
    CompetencyQualificationView,
    LearnerState,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
    VerificationClass,
    VerificationProbeView,
)

_REQUIRED_CLASSES: tuple[VerificationClass, ...] = (
    "independent",
    "retention_7d",
    "retention_30d",
    "transfer",
)
_MAX_PROBES = 96


class QualificationTransitionError(ValueError):
    """Base class for fail-closed qualification transition errors."""


class UnknownProbeError(QualificationTransitionError):
    """A trusted probe verdict references no scheduled probe."""


class ProbeBindingMismatchError(QualificationTransitionError):
    """The verdict does not match the scheduled competency/proof class."""


class ProbeNotDueError(QualificationTransitionError):
    """A delayed retention probe was evaluated before its server-owned due time."""


class ProbeAlreadyEvaluatedError(QualificationTransitionError):
    """A completed probe cannot be rewritten by a different verdict."""


@dataclass(frozen=True, slots=True)
class QualificationTransitionResult:
    state: LearnerState
    changed: bool


def apply_evidence_qualification(
    *,
    state: LearnerState,
    verdict: TrustedEvidenceVerdict,
    occurred_at: datetime,
) -> QualificationTransitionResult:
    """Translate a trusted evidence verdict into qualification state and future obligations."""
    current = state.competency_qualification.get(
        verdict.competency_id,
        CompetencyQualificationState(competency_id=verdict.competency_id),
    )
    independent_ids = list(current.independent_evidence_ids)
    assisted_ids = list(current.assisted_evidence_ids)
    satisfied = list(current.satisfied_classes)
    probes = list(state.verification_probes)

    if verdict.disposition != "accepted":
        return QualificationTransitionResult(state=state, changed=False)

    independent = (
        verdict.independence == "independent"
        and verdict.assistance == "none"
        and verdict.reasoning == "verified"
    )
    if not independent:
        if verdict.evidence_id in assisted_ids:
            return QualificationTransitionResult(state=state, changed=False)
        assisted_ids.append(verdict.evidence_id)
        qualification = current.model_copy(
            update={
                "assisted_evidence_ids": assisted_ids,
                "last_updated_at": occurred_at.isoformat(),
            }
        )
        return QualificationTransitionResult(
            state=state.model_copy(
                update={
                    "competency_qualification": {
                        **state.competency_qualification,
                        verdict.competency_id: qualification,
                    }
                }
            ),
            changed=True,
        )

    if verdict.evidence_id not in independent_ids:
        independent_ids.append(verdict.evidence_id)
    if "independent" not in satisfied:
        satisfied.append("independent")

    for verification_class, delay in (
        ("transfer", timedelta()),
        ("retention_7d", timedelta(days=7)),
        ("retention_30d", timedelta(days=30)),
    ):
        if any(
            item.competency_id == verdict.competency_id
            and item.verification_class == verification_class
            and item.status in {"scheduled", "passed"}
            for item in probes
        ):
            continue
        due_at = occurred_at + delay
        probes.append(
            _probe(
                learner_id=state.learner_id,
                competency_id=verdict.competency_id,
                verification_class=verification_class,
                source_evidence_id=verdict.evidence_id,
                due_at=due_at,
            )
        )

    qualification = current.model_copy(
        update={
            "independent_evidence_ids": independent_ids,
            "assisted_evidence_ids": assisted_ids,
            "satisfied_classes": _ordered_classes(satisfied),
            "last_updated_at": occurred_at.isoformat(),
        }
    )
    return QualificationTransitionResult(
        state=state.model_copy(
            update={
                "competency_qualification": {
                    **state.competency_qualification,
                    verdict.competency_id: qualification,
                },
                "verification_probes": probes[-_MAX_PROBES:],
            }
        ),
        changed=True,
    )


def apply_probe_verdict(
    *,
    state: LearnerState,
    verdict: TrustedProbeVerdict,
    occurred_at: datetime,
) -> QualificationTransitionResult:
    """Apply one exact scheduled no-hint proof verdict and reopen qualification on failure."""
    index = next(
        (idx for idx, item in enumerate(state.verification_probes) if item.probe_id == verdict.probe_id),
        None,
    )
    if index is None:
        raise UnknownProbeError
    probe = state.verification_probes[index]
    if (
        probe.competency_id != verdict.competency_id
        or probe.verification_class != verdict.verification_class
    ):
        raise ProbeBindingMismatchError

    evaluation_id = _digest(
        "|".join(
            (
                verdict.probe_id,
                verdict.competency_id,
                verdict.verification_class,
                verdict.disposition,
                verdict.independence,
                verdict.assistance,
                verdict.reasoning,
                verdict.evaluator_id,
                verdict.evaluator_version,
                str(verdict.confidence),
            )
        ),
        24,
    )
    if probe.status != "scheduled":
        if probe.evaluation_id == evaluation_id:
            return QualificationTransitionResult(state=state, changed=False)
        raise ProbeAlreadyEvaluatedError

    due_at = datetime.fromisoformat(probe.due_at)
    if occurred_at < due_at:
        raise ProbeNotDueError

    qualifies = (
        verdict.disposition == "passed"
        and verdict.independence == "independent"
        and verdict.assistance == "none"
        and verdict.reasoning == "verified"
    )
    next_status = "passed" if qualifies else "failed"
    updated_probe = probe.model_copy(
        update={
            "status": next_status,
            "completed_at": occurred_at.isoformat(),
            "evaluation_id": evaluation_id,
            "evaluator_id": verdict.evaluator_id,
            "evaluator_version": verdict.evaluator_version,
        }
    )
    probes = list(state.verification_probes)
    probes[index] = updated_probe

    current = state.competency_qualification.get(
        verdict.competency_id,
        CompetencyQualificationState(competency_id=verdict.competency_id),
    )
    satisfied = list(current.satisfied_classes)
    failed = list(current.failed_classes)
    if qualifies:
        if verdict.verification_class not in satisfied:
            satisfied.append(verdict.verification_class)
        failed = [item for item in failed if item != verdict.verification_class]
    else:
        satisfied = [item for item in satisfied if item != verdict.verification_class]
        if verdict.verification_class not in failed:
            failed.append(verdict.verification_class)

    qualification = current.model_copy(
        update={
            "satisfied_classes": _ordered_classes(satisfied),
            "failed_classes": _ordered_classes(failed),
            "last_updated_at": occurred_at.isoformat(),
        }
    )
    return QualificationTransitionResult(
        state=state.model_copy(
            update={
                "competency_qualification": {
                    **state.competency_qualification,
                    verdict.competency_id: qualification,
                },
                "verification_probes": probes,
            }
        ),
        changed=True,
    )


def project_qualifications(state: LearnerState) -> list[CompetencyQualificationView]:
    """Project exact proof classes without converting them into a generic readiness score."""
    competency_ids = sorted(
        set(state.competency_evidence)
        | set(state.competency_qualification)
        | {item.competency_id for item in state.verification_probes}
    )
    result: list[CompetencyQualificationView] = []
    for competency_id in competency_ids:
        current = state.competency_qualification.get(
            competency_id,
            CompetencyQualificationState(competency_id=competency_id),
        )
        satisfied = _ordered_classes(current.satisfied_classes)
        missing = [item for item in _REQUIRED_CLASSES if item not in satisfied]
        scheduled = [
            item
            for item in state.verification_probes
            if item.competency_id == competency_id and item.status == "scheduled"
        ]
        result.append(
            CompetencyQualificationView(
                competency_id=competency_id,
                satisfied_classes=satisfied,
                missing_classes=missing,
                failed_classes=_ordered_classes(current.failed_classes),
                independent_evidence_ids=list(current.independent_evidence_ids),
                assisted_evidence_ids=list(current.assisted_evidence_ids),
                scheduled_probe_ids=[item.probe_id for item in scheduled],
                next_probe_at=min((item.due_at for item in scheduled), default=None),
                fully_qualified=not missing,
            )
        )
    return result


def _probe(
    *,
    learner_id: str,
    competency_id: str,
    verification_class: VerificationClass,
    source_evidence_id: str,
    due_at: datetime,
) -> VerificationProbeView:
    probe_id = "probe-" + _digest(
        "|".join(
            (
                learner_id,
                competency_id,
                verification_class,
                source_evidence_id,
                due_at.isoformat(),
            )
        ),
        24,
    )
    unseen_fingerprint = ""
    if verification_class == "transfer":
        unseen_fingerprint = "transfer-" + _digest(
            f"{learner_id}|{competency_id}|{source_evidence_id}|unseen-transfer",
            24,
        )
    return VerificationProbeView(
        probe_id=probe_id,
        competency_id=competency_id,
        verification_class=verification_class,
        source_evidence_id=source_evidence_id,
        due_at=due_at.isoformat(),
        unseen_instance_fingerprint=unseen_fingerprint,
    )


def _ordered_classes(values: list[VerificationClass]) -> list[VerificationClass]:
    return [item for item in _REQUIRED_CLASSES if item in values]


def _digest(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
