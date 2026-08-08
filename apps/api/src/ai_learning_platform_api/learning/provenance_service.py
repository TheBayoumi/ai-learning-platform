"""G07 service extension for immutable work provenance and independent defense."""

from __future__ import annotations

from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.provenance import (
    WorkProvenanceError,
    apply_work_provenance_verdict,
    capture_work_provenance,
    issue_work_challenges,
    project_work_provenance,
)
from ai_learning_platform_api.learning.qualification_service import QualificationLearningPlanService
from ai_learning_platform_api.learning.schemas import (
    LearnerState,
    PlanView,
    TrustedEvidenceVerdict,
    TrustedWorkProvenanceVerdict,
    WorkProvenanceSubmission,
)
from ai_learning_platform_api.learning.service import LearningPlanError


class ProvenanceLearningPlanService(QualificationLearningPlanService):
    """Add work authorship/provenance verification before high-stakes evidence acceptance."""

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
        base = super()._project(state, role)
        return base.model_copy(update={"work_provenance": project_work_provenance(state)})

    def issue_work_verification(
        self,
        *,
        state_token: str,
        evidence_id: str,
    ) -> PlanView:
        state, role = self._state_and_role(state_token)
        result = issue_work_challenges(
            state=state,
            evidence_id=evidence_id,
            occurred_at=self._clock(),
        )
        if not result.changed:
            return self._project(state, role)
        updated = result.state.model_copy(update={"sequence": result.state.sequence + 1})
        return self._project(updated, role)

    def submit_work_provenance(
        self,
        *,
        state_token: str,
        submission: WorkProvenanceSubmission,
    ) -> PlanView:
        state, role = self._state_and_role(state_token)
        result = capture_work_provenance(
            state=state,
            submission=submission,
            occurred_at=self._clock(),
        )
        if not result.changed:
            return self._project(state, role)
        updated = result.state.model_copy(update={"sequence": result.state.sequence + 1})
        return self._project(updated, role)

    def evaluate_work_provenance(
        self,
        *,
        state_token: str,
        verdict: TrustedWorkProvenanceVerdict,
    ) -> PlanView:
        state, role = self._state_and_role(state_token)
        result = apply_work_provenance_verdict(
            state=state,
            verdict=verdict,
            occurred_at=self._clock(),
        )
        if not result.changed:
            return self._project(state, role)
        updated = result.state.model_copy(update={"sequence": result.state.sequence + 1})
        return self._project(updated, role)

    def evaluate_evidence(
        self,
        *,
        state_token: str,
        verdict: TrustedEvidenceVerdict,
    ) -> PlanView:
        """Require verified provenance before accepting work into authoritative qualification."""
        state, _ = self._state_and_role(state_token)
        evidence = next(
            (item for item in state.evidence_history if item.evidence_id == verdict.evidence_id),
            None,
        )
        if evidence is None:
            return super().evaluate_evidence(state_token=state_token, verdict=verdict)
        if verdict.disposition == "accepted" and evidence.source_high_stakes_eligible:
            provenance = state.work_provenance.get(verdict.evidence_id)
            if provenance is None or not provenance.eligible_for_readiness:
                raise WorkProvenanceError(
                    "verified work provenance is required before high-stakes evidence acceptance"
                )
        return super().evaluate_evidence(state_token=state_token, verdict=verdict)

    def _state_and_role(self, state_token: str) -> tuple[LearnerState, RoleDefinition]:
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise LearningPlanError
        return self._upgrade_state(state, role), role


__all__ = ["ProvenanceLearningPlanService"]
