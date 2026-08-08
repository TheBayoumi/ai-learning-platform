"""G08 service extension for deterministic role-readiness blocker projection."""

from __future__ import annotations

from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.provenance_service import ProvenanceLearningPlanService
from ai_learning_platform_api.learning.readiness import project_readiness
from ai_learning_platform_api.learning.schemas import LearnerState, PlanView


class ReadinessLearningPlanService(ProvenanceLearningPlanService):
    """Project readiness evidence without granting an external readiness claim."""

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
        base = super()._project(state, role)
        readiness = project_readiness(
            state=state,
            role=role,
            target=base.target,
        )
        return base.model_copy(
            update={
                "claim_state": "validation_locked",
                "verified_readiness_percent": None,
                "readiness_projection": readiness,
            }
        )


__all__ = ["ReadinessLearningPlanService"]
