"""Bounded operational audit helpers for durable learner exports."""

from __future__ import annotations

import json

from ai_learning_platform_api.persistence.contracts import StoredLearnerState
from ai_learning_platform_api.persistence.schemas import LearnerOperationalAuditView

_MAX_RAW_STATE_BYTES = 262_144
_MAX_EVIDENCE_HISTORY = 24
_MAX_EVALUATIONS = 64
_MAX_PLAN_VERSIONS = 3
_MAX_VERIFICATION_PROBES = 96
_MAX_WORK_PROVENANCE = 32
_MAX_ACTIVE_EXPOSURES = 16


def audit_stored_state(
    stored: StoredLearnerState,
    *,
    replay: StoredLearnerState | None,
) -> LearnerOperationalAuditView:
    """Project resource, replay, and claim-integrity invariants without exposing secrets."""
    state = stored.state
    raw_state_bytes = len(
        json.dumps(
            state.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    replay_verified = (
        replay is not None
        and replay.account_id == stored.account_id
        and replay.learner_id == stored.learner_id
        and replay.version == stored.version
        and replay.state == stored.state
    )
    active = next(
        (
            item
            for item in state.plan_versions
            if item.plan_version_id == state.active_plan_version_id
        ),
        None,
    )
    active_exposure_count = len(active.task_exposures) if active is not None else 0
    claim_integrity_verified = state.target is not None and all(
        item.status in {"unverified", "partial", "independent"}
        for item in state.competency_evidence.values()
    )
    within_resource_bounds = (
        raw_state_bytes <= _MAX_RAW_STATE_BYTES
        and len(state.evidence_history) <= _MAX_EVIDENCE_HISTORY
        and len(state.evidence_evaluations) <= _MAX_EVALUATIONS
        and len(state.plan_versions) <= _MAX_PLAN_VERSIONS
        and len(state.verification_probes) <= _MAX_VERIFICATION_PROBES
        and len(state.work_provenance) <= _MAX_WORK_PROVENANCE
        and active_exposure_count <= _MAX_ACTIVE_EXPOSURES
    )
    return LearnerOperationalAuditView(
        raw_state_bytes=raw_state_bytes,
        evidence_records=len(state.evidence_history),
        evaluation_records=len(state.evidence_evaluations),
        retained_plan_versions=len(state.plan_versions),
        verification_probes=len(state.verification_probes),
        work_provenance_records=len(state.work_provenance),
        active_task_exposures=active_exposure_count,
        replay_verified=replay_verified,
        claim_integrity_verified=claim_integrity_verified,
        within_resource_bounds=within_resource_bounds,
    )
