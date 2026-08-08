"""Deterministic readiness blocker projection over trusted evidence, proof, and work provenance."""

from __future__ import annotations

from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.qualification import project_qualifications
from ai_learning_platform_api.learning.role_profile import profile_for
from ai_learning_platform_api.learning.schemas import (
    CompetencyReadinessView,
    LearnerState,
    ReadinessProjectionView,
    TargetView,
)

_REQUIRED_PROOF_CLASSES = ("independent", "retention_7d", "retention_30d", "transfer")


def project_readiness(
    *,
    state: LearnerState,
    role: RoleDefinition,
    target: TargetView,
) -> ReadinessProjectionView:
    """Project exact mandatory blockers without inventing a score or external approval."""
    graph = profile_for(role)
    qualifications = {item.competency_id: item for item in project_qualifications(state)}
    evidence_by_id = {item.evidence_id: item for item in state.evidence_history}
    active_misconceptions: dict[str, list[str]] = {}
    for item in state.misconceptions:
        if item.status == "active":
            active_misconceptions.setdefault(item.competency_id, []).append(item.code)

    competency_views: list[CompetencyReadinessView] = []
    disputed_evidence_ids: list[str] = []
    verified_work_evidence_ids: list[str] = []

    for competency in role.competencies:
        competency_id = competency.identifier
        evidence_state = state.competency_evidence.get(competency_id)
        accepted_ids = list(evidence_state.accepted_evidence_ids) if evidence_state else []
        disputed_ids = list(evidence_state.disputed_evidence_ids) if evidence_state else []
        disputed_evidence_ids.extend(disputed_ids)
        qualification = qualifications.get(competency_id)
        satisfied_classes = list(qualification.satisfied_classes) if qualification else []
        missing_classes = [
            item for item in _REQUIRED_PROOF_CLASSES if item not in satisfied_classes
        ]
        eligible_work_ids = [
            evidence_id
            for evidence_id in accepted_ids
            if evidence_id in state.work_provenance
            and state.work_provenance[evidence_id].eligible_for_readiness
            and evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].competency_id == competency_id
        ]
        verified_work_evidence_ids.extend(eligible_work_ids)
        misconception_codes = sorted(active_misconceptions.get(competency_id, []))
        blockers: list[str] = []
        if evidence_state is None or evidence_state.status != "independent":
            blockers.append("independent_evidence_missing")
        if disputed_ids:
            blockers.append("disputed_evidence_present")
        if missing_classes:
            blockers.append("proof_classes_incomplete")
        if not eligible_work_ids:
            blockers.append("verified_work_provenance_missing")
        if misconception_codes:
            blockers.append("active_misconception")

        competency_views.append(
            CompetencyReadinessView(
                competency_id=competency_id,
                competency_name=competency.name,
                mandatory=True,
                evidence_status=(evidence_state.status if evidence_state else "unverified"),
                accepted_evidence_ids=accepted_ids,
                disputed_evidence_ids=disputed_ids,
                satisfied_proof_classes=satisfied_classes,
                missing_proof_classes=missing_classes,
                verified_work_evidence_ids=eligible_work_ids,
                active_misconception_codes=misconception_codes,
                blocker_codes=blockers,
                engineering_complete=not blockers,
            )
        )

    mandatory_gap_ids = [
        item.competency_id for item in competency_views if not item.engineering_complete
    ]
    active_overlays = _active_overlays(target)
    unresolved_overlay_deltas = active_overlays if target.validation_state != "approved" else []
    uncertainties: list[str] = []
    if role.validation_state != "approved":
        uncertainties.append("role_profile_external_validation_pending")
    if target.validation_state != "approved":
        uncertainties.append("target_external_validation_pending")
    if unresolved_overlay_deltas:
        uncertainties.append("overlay_deltas_not_externally_validated")
    # Evidence currently has no expiry metadata. Do not invent a freshness window or mark
    # accepted evidence stale without an explicit policy/versioned expiry contract.
    uncertainties.append("evidence_staleness_not_computable_without_expiry_metadata")

    profile_binding_valid = (
        target.role_id == role.identifier
        and target.role_version == role.version
        and graph.role_id == role.identifier
        and graph.role_version == role.version
    )
    if not profile_binding_valid:
        uncertainties.append("target_role_profile_version_mismatch")

    engineering_evidence_complete = not mandatory_gap_ids and profile_binding_valid
    return ReadinessProjectionView(
        role_id=role.identifier,
        role_version=role.version,
        graph_version=graph.graph_version,
        evidence_policy_version=graph.evidence_policy_version,
        target_role_id=target.role_id,
        target_role_version=target.role_version,
        target_validation_state=target.validation_state,
        role_validation_state=role.validation_state,
        claim_state="validation_locked",
        engineering_evidence_complete=engineering_evidence_complete,
        external_approval_required=True,
        mandatory_competency_ids=[item.identifier for item in role.competencies],
        mandatory_gap_ids=mandatory_gap_ids,
        disputed_evidence_ids=sorted(set(disputed_evidence_ids)),
        stale_evidence_ids=[],
        verified_work_evidence_ids=sorted(set(verified_work_evidence_ids)),
        active_overlays=active_overlays,
        unresolved_overlay_deltas=unresolved_overlay_deltas,
        exclusions=list(target.exclusions),
        uncertainties=sorted(set(uncertainties)),
        competencies=competency_views,
    )


def _active_overlays(target: TargetView) -> list[str]:
    values = [f"stack:{item}" for item in target.stack_overlays]
    if target.industry_overlay:
        values.append(f"industry:{target.industry_overlay}")
    if target.company_overlay:
        values.append(f"company:{target.company_overlay}")
    return values
