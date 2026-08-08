"""Pure deterministic curriculum ranking for learner-specific plan versions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ai_learning_platform_api.learning.catalog import CompetencyDefinition, RoleDefinition
from ai_learning_platform_api.learning.role_profile import CompetencyProfile, profile_for
from ai_learning_platform_api.learning.schemas import (
    CompetencyEvidenceState,
    CompetencyEvidenceStatus,
    MisconceptionRecord,
    PlanPrioritySnapshot,
    TargetView,
)

_EVIDENCE_GAP = {"unverified": 100, "partial": 55, "independent": 0}


@dataclass(frozen=True, slots=True)
class CurriculumDecision:
    """One replayable competency scheduling decision."""

    competency: CompetencyDefinition
    profile: CompetencyProfile
    evidence_status: CompetencyEvidenceStatus
    diagnostic_signal_percent: int
    authoritative_gap_percent: int
    blocked_by: tuple[str, ...]
    active_misconception_codes: tuple[str, ...]
    focused: bool
    score: int
    reason: str

    def snapshot(self, rank: int) -> PlanPrioritySnapshot:
        return PlanPrioritySnapshot(
            competency_id=self.competency.identifier,
            rank=rank,
            evidence_status=self.evidence_status,
            diagnostic_signal_percent=self.diagnostic_signal_percent,
            authoritative_gap_percent=self.authoritative_gap_percent,
            prerequisite_ids=list(self.profile.prerequisites),
            blocked_by=list(self.blocked_by),
            active_misconception_codes=list(self.active_misconception_codes),
            focused=self.focused,
            reason=self.reason,
        )


def diagnostic_signal_values(
    role: RoleDefinition,
    planning_signal: dict[str, int],
    assessment_scores: dict[str, int],
) -> dict[str, int]:
    """Blend non-authoritative signals only for ordering unresolved work."""
    return {
        competency.identifier: (
            round(
                (planning_signal.get(competency.identifier, 0) * 0.7)
                + (assessment_scores[competency.identifier] * 0.3)
            )
            if competency.identifier in assessment_scores
            else planning_signal.get(competency.identifier, 0)
        )
        for competency in role.competencies
    }


def rank_curriculum(
    *,
    role: RoleDefinition,
    planning_signal: dict[str, int],
    assessment_scores: dict[str, int],
    competency_evidence: dict[str, CompetencyEvidenceState],
    misconceptions: list[MisconceptionRecord],
    focus_competency_ids: list[str],
) -> tuple[CurriculumDecision, ...]:
    """Rank from authoritative gaps first; diagnostics only break unresolved ties."""
    graph = profile_for(role)
    known_ids = {item.identifier for item in role.competencies}
    diagnostic = diagnostic_signal_values(role, planning_signal, assessment_scores)
    active_by_competency: dict[str, list[str]] = {}
    for item in misconceptions:
        if item.status == "active" and item.competency_id in known_ids:
            active_by_competency.setdefault(item.competency_id, []).append(item.code)

    decisions: list[CurriculumDecision] = []
    for competency in role.competencies:
        competency_profile = graph.competencies[competency.identifier]
        evidence = competency_evidence.get(
            competency.identifier,
            CompetencyEvidenceState(competency_id=competency.identifier),
        )
        blocked_by = tuple(
            prerequisite
            for prerequisite in competency_profile.prerequisites
            if competency_evidence.get(
                prerequisite,
                CompetencyEvidenceState(competency_id=prerequisite),
            ).status
            != "independent"
        )
        misconception_codes = tuple(
            sorted(set(active_by_competency.get(competency.identifier, [])))
        )
        focused = competency.identifier in focus_competency_ids
        authoritative_gap = _EVIDENCE_GAP[evidence.status]
        diagnostic_gap = 100 - diagnostic.get(competency.identifier, 0)
        score = (
            (authoritative_gap * competency.weight * 100)
            + (diagnostic_gap * 10)
            + (min(len(misconception_codes), 3) * 2_000)
            + (1_500 if focused else 0)
        )
        reason_parts = [
            f"authoritative evidence={evidence.status}",
            f"authoritative gap={authoritative_gap}%",
            f"diagnostic ordering signal={diagnostic.get(competency.identifier, 0)}%",
            f"weight={competency.weight}",
        ]
        if blocked_by:
            reason_parts.append(f"blocked by prerequisites={','.join(blocked_by)}")
        if misconception_codes:
            reason_parts.append(
                f"active misconceptions={','.join(misconception_codes)}"
            )
        if focused:
            reason_parts.append("explicit learner focus")
        reason_parts.append(
            "self-report/calibration may order unresolved work but cannot satisfy evidence"
        )
        decisions.append(
            CurriculumDecision(
                competency=competency,
                profile=competency_profile,
                evidence_status=evidence.status,
                diagnostic_signal_percent=diagnostic.get(competency.identifier, 0),
                authoritative_gap_percent=authoritative_gap,
                blocked_by=blocked_by,
                active_misconception_codes=misconception_codes,
                focused=focused,
                score=score,
                reason="; ".join(reason_parts),
            )
        )

    decisions.sort(
        key=lambda item: (
            bool(item.blocked_by),
            item.evidence_status == "independent",
            -item.score,
            item.competency.identifier,
        )
    )
    return tuple(decisions)


def eligible_build_decisions(
    decisions: tuple[CurriculumDecision, ...],
) -> tuple[CurriculumDecision, ...]:
    """Return only unresolved competencies whose prerequisites are evidenced."""
    return tuple(
        item
        for item in decisions
        if item.evidence_status != "independent" and not item.blocked_by
    )


def target_fingerprint(target: TargetView) -> str:
    """Hash the exact resolved Target into every immutable plan version."""
    payload = json.dumps(
        target.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def plan_version_id(
    *,
    learner_id: str,
    role_version: str,
    revision: int,
    target_hash: str,
    trigger: str,
    activity_ids: list[str],
    priority_ids: list[str],
) -> str:
    """Create a stable content-bound identifier for one plan version."""
    payload = "|".join(
        (
            learner_id,
            role_version,
            str(revision),
            target_hash,
            trigger,
            ",".join(activity_ids),
            ",".join(priority_ids),
        )
    )
    return f"plan-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"
