"""Learner diagnosis, planning, signed state, and trusted served-instance domain."""

from ai_learning_platform_api.learning import schemas as _schemas
from ai_learning_platform_api.learning import service as _service
from ai_learning_platform_api.learning.blueprint_contracts import (
    TrustedActivityView,
    TrustedAssessmentSubmissionView,
    TrustedLearnerPlanVersion,
    TrustedLearnerState,
    TrustedPlanView,
)
from ai_learning_platform_api.learning.blueprint_service import BlueprintLearningPlanService

# G05 is a backward-compatible contract extension: legacy state parses with safe defaults, while
# all new service transitions use the richer subclasses. Patch the already-loaded module globals so
# direct imports of learning.service and persistence orchestration share one deterministic owner.
_service.ActivityView = TrustedActivityView
_service.LearnerPlanVersion = TrustedLearnerPlanVersion
_service.LearnerState = TrustedLearnerState
_service.PlanView = TrustedPlanView
_service.AssessmentSubmissionView = TrustedAssessmentSubmissionView
_service.LearningPlanService = BlueprintLearningPlanService

_schemas.ActivityView = TrustedActivityView
_schemas.LearnerPlanVersion = TrustedLearnerPlanVersion
_schemas.LearnerState = TrustedLearnerState
_schemas.PlanView = TrustedPlanView
_schemas.AssessmentSubmissionView = TrustedAssessmentSubmissionView

LearningPlanService = BlueprintLearningPlanService

__all__ = ["LearningPlanService"]
