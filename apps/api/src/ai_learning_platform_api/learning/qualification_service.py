"""G06 service extension for server-timed retention and unseen-transfer proof classes."""

from __future__ import annotations

from ai_learning_platform_api.learning.blueprint_service import BlueprintLearningPlanService
from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.qualification import (
    apply_evidence_qualification,
    apply_probe_verdict,
    project_qualifications,
)
from ai_learning_platform_api.learning.schemas import (
    LearnerState,
    PlanView,
    TrustedEvidenceVerdict,
    TrustedProbeVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanError


class QualificationLearningPlanService(BlueprintLearningPlanService):
    """Extend trusted evidence with exact independent/retention/transfer proof state."""

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
        base = super()._project(state, role)
        return base.model_copy(
            update={
                "qualifications": project_qualifications(state),
                "verification_probes": list(state.verification_probes),
            }
        )

    def evaluate_evidence(
        self,
        *,
        state_token: str,
        verdict: TrustedEvidenceVerdict,
    ) -> PlanView:
        before = self._codec.decode(state_token)
        projected = super().evaluate_evidence(state_token=state_token, verdict=verdict)
        if projected.sequence == before.sequence:
            return projected
        state = self._codec.decode(projected.state_token)
        evaluation = next(
            (
                item
                for item in reversed(state.evidence_evaluations)
                if item.evidence_id == verdict.evidence_id
            ),
            None,
        )
        if evaluation is None:
            return projected
        occurred_at = self._parse_datetime(evaluation.occurred_at)
        result = apply_evidence_qualification(
            state=state,
            verdict=verdict,
            occurred_at=occurred_at,
        )
        if not result.changed:
            return projected
        role = ROLE_CATALOG.get(result.state.target_role)
        if role is None:
            raise LearningPlanError
        updated = result.state.model_copy(update={"sequence": result.state.sequence + 1})
        return self._project(updated, role)

    def evaluate_probe(
        self,
        *,
        state_token: str,
        verdict: TrustedProbeVerdict,
    ) -> PlanView:
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise LearningPlanError
        state = self._upgrade_state(state, role)
        result = apply_probe_verdict(
            state=state,
            verdict=verdict,
            occurred_at=self._clock(),
        )
        if not result.changed:
            return self._project(state, role)
        updated = result.state.model_copy(update={"sequence": result.state.sequence + 1})
        return self._project(updated, role)

    @staticmethod
    def _parse_datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)


__all__ = ["QualificationLearningPlanService"]
