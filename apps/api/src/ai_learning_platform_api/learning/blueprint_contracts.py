"""Structured G05 contracts for trusted blueprints and learner-bound served instances."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    AssessmentSubmissionView,
    LearnerPlanVersion,
    LearnerState,
    PlanView,
    StrictModel,
)

BlueprintTrustState = Literal["legacy_unverified", "trusted"]


class TaskExposureView(StrictModel):
    """One persisted served-instance exposure used for replay and collision rejection."""

    instance_id: str
    item_family_id: str
    item_family_version: str
    blueprint_id: str
    blueprint_version: str
    rubric_version: str
    plan_version_id: str
    semantic_fingerprint: str
    semantic_tokens: list[str] = Field(default_factory=list, max_length=12)
    high_stakes_eligible: bool = False
    served_at: str


class TrustedActivityView(ActivityView):
    """Activity projection carrying explicit blueprint trust and instance traceability."""

    item_family_id: str = ""
    item_family_version: str = ""
    item_family_trust: BlueprintTrustState = "legacy_unverified"
    blueprint_id: str = ""
    blueprint_version: str = ""
    blueprint_trust: BlueprintTrustState = "legacy_unverified"
    rubric_version: str = ""
    instance_seed: str = ""
    semantic_fingerprint: str = ""
    semantic_tokens: list[str] = Field(default_factory=list, max_length=12)
    scenario_tags: list[str] = Field(default_factory=list, max_length=8)
    plan_version_id: str = ""
    high_stakes_eligible: bool = False


class TrustedLearnerPlanVersion(LearnerPlanVersion):
    """Plan snapshot with cumulative bounded exposure history for collision-safe replanning."""

    activities: list[TrustedActivityView]
    task_exposures: list[TaskExposureView] = Field(default_factory=list, max_length=64)


class TrustedLearnerState(LearnerState):
    """Backward-compatible learner state upgraded with trusted task-instance contracts."""

    activities: list[TrustedActivityView]
    plan_versions: list[TrustedLearnerPlanVersion] = Field(default_factory=list)


class TrustedPlanView(PlanView):
    """Public plan projection exposing exact blueprint and served-instance provenance."""

    current_activity: TrustedActivityView | None
    active_plan_version: TrustedLearnerPlanVersion
    plan_history: list[TrustedLearnerPlanVersion]


class TrustedAssessmentSubmissionView(AssessmentSubmissionView):
    """Assessment result preserving the trusted task-instance plan projection."""

    plan: TrustedPlanView
