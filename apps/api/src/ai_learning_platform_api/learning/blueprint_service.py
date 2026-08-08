"""G05 service extension that binds trusted catalog blueprints to learner-specific instances."""

from __future__ import annotations

import hashlib
from datetime import datetime

from ai_learning_platform_api.learning.blueprint_contracts import (
    TaskExposureView,
    TrustedActivityView,
    TrustedLearnerPlanVersion,
)
from ai_learning_platform_api.learning.blueprints import (
    BlueprintTrustError,
    attach_blueprint_identity,
    bind_learner_instance,
    exposure_from_activity,
)
from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.planner import CurriculumDecision, target_fingerprint
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CurriculumTrigger,
    LearnerPlanVersion,
    PlanView,
    TargetView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import (
    LearningPlanError,
    LearningPlanService as BaseLearningPlanService,
)

_MAX_TASK_EXPOSURES = 64


class UntrustedInstanceEvidenceError(LearningPlanError):
    """Trusted evaluator evidence cannot be accepted from an untrusted generated instance."""

    code = "UNTRUSTED_TASK_INSTANCE"


class BlueprintLearningPlanService(BaseLearningPlanService):
    """Preserve the G03/G04 planner while enforcing G05 blueprint trust and uniqueness."""

    @staticmethod
    def _activity_view(
        *,
        role: RoleDefinition,
        decision: CurriculumDecision,
        seed: str,
        position: int,
        learner_name: str,
        experience_summary: str,
        generation: int,
    ) -> TrustedActivityView:
        base = BaseLearningPlanService._activity_view(
            role=role,
            decision=decision,
            seed=seed,
            position=position,
            learner_name=learner_name,
            experience_summary=experience_summary,
            generation=generation,
        )
        trusted = TrustedActivityView.model_validate(base.model_dump(mode="json"))
        return attach_blueprint_identity(role=role, activity=trusted)

    @staticmethod
    def _review_activity(
        *,
        source: ActivityView,
        learner_name: str,
        generation: int,
        available_from: datetime,
    ) -> TrustedActivityView:
        base = BaseLearningPlanService._review_activity(
            source=source,
            learner_name=learner_name,
            generation=generation,
            available_from=available_from,
        )
        trusted_source = TrustedActivityView.model_validate(source.model_dump(mode="json"))
        review = TrustedActivityView.model_validate(base.model_dump(mode="json"))
        seed = hashlib.sha256(
            f"review|{source.id}|{generation}|{available_from.isoformat()}".encode()
        ).hexdigest()
        return review.model_copy(
            update={
                "item_family_id": trusted_source.item_family_id,
                "item_family_version": trusted_source.item_family_version,
                "item_family_trust": trusted_source.item_family_trust,
                "blueprint_id": trusted_source.blueprint_id,
                "blueprint_version": trusted_source.blueprint_version,
                "blueprint_trust": trusted_source.blueprint_trust,
                "rubric_version": trusted_source.rubric_version,
                "instance_seed": seed,
                "semantic_fingerprint": hashlib.sha256(
                    f"review|{trusted_source.semantic_fingerprint}|{generation}".encode()
                ).hexdigest()[:32],
                "semantic_tokens": [
                    f"review:{trusted_source.blueprint_id}",
                    f"source:{trusted_source.semantic_fingerprint}",
                ],
                "scenario_tags": ["delayed-review", f"source:{source.id}"],
                "high_stakes_eligible": False,
            }
        )

    def _plan_version(
        self,
        *,
        learner_id: str,
        role: RoleDefinition,
        target: TargetView,
        revision: int,
        created_at: datetime,
        trigger: CurriculumTrigger,
        weekly_hours: int,
        focus_competency_ids: list[str],
        decisions: tuple[CurriculumDecision, ...],
        activities: list[ActivityView],
        previous: LearnerPlanVersion | None,
    ) -> TrustedLearnerPlanVersion:
        prior_exposures = (
            list(previous.task_exposures) if isinstance(previous, TrustedLearnerPlanVersion) else []
        )
        target_hash = target_fingerprint(target)
        bound: list[TrustedActivityView] = []
        collision_scope = list(prior_exposures)
        for position, raw_activity in enumerate(activities, start=1):
            activity = TrustedActivityView.model_validate(raw_activity.model_dump(mode="json"))
            if activity.kind == "build":
                activity = bind_learner_instance(
                    role=role,
                    activity=activity,
                    learner_id=learner_id,
                    target_fingerprint=target_hash,
                    revision=revision,
                    position=position,
                    exposures=collision_scope,
                )
                collision_scope.append(
                    TaskExposureView(
                        instance_id=activity.id,
                        item_family_id=activity.item_family_id,
                        item_family_version=activity.item_family_version,
                        blueprint_id=activity.blueprint_id,
                        blueprint_version=activity.blueprint_version,
                        rubric_version=activity.rubric_version,
                        plan_version_id="pending",
                        semantic_fingerprint=activity.semantic_fingerprint,
                        semantic_tokens=list(activity.semantic_tokens),
                        high_stakes_eligible=True,
                        served_at=created_at.isoformat(),
                    )
                )
            bound.append(activity)
        activities[:] = bound
        base_version = super()._plan_version(
            learner_id=learner_id,
            role=role,
            target=target,
            revision=revision,
            created_at=created_at,
            trigger=trigger,
            weekly_hours=weekly_hours,
            focus_competency_ids=focus_competency_ids,
            decisions=decisions,
            activities=activities,
            previous=previous,
        )
        plan_version_id = base_version.plan_version_id
        finalized = [
            activity.model_copy(update={"plan_version_id": plan_version_id}) for activity in bound
        ]
        activities[:] = finalized
        current_exposures = [
            exposure_from_activity(
                activity=activity,
                plan_version_id=plan_version_id,
                served_at=created_at.isoformat(),
            )
            for activity in finalized
            if activity.instance_seed and activity.semantic_fingerprint
        ]
        exposure_history = [*prior_exposures, *current_exposures][-_MAX_TASK_EXPOSURES:]
        payload = base_version.model_dump(mode="json")
        payload["activities"] = [item.model_dump(mode="json") for item in finalized]
        payload["task_exposures"] = [item.model_dump(mode="json") for item in exposure_history]
        return TrustedLearnerPlanVersion.model_validate(payload)

    def evaluate_evidence(
        self,
        *,
        state_token: str,
        verdict: TrustedEvidenceVerdict,
    ) -> PlanView:
        """Reject high-stakes evaluator promotion when the source task was not trusted."""
        state = self._codec.decode(state_token)
        evidence = next(
            (item for item in state.evidence_history if item.evidence_id == verdict.evidence_id),
            None,
        )
        if evidence is None:
            return super().evaluate_evidence(state_token=state_token, verdict=verdict)
        activities = [
            activity for version in state.plan_versions for activity in version.activities
        ]
        source = next((item for item in activities if item.id == evidence.activity_id), None)
        if source is None or not isinstance(source, TrustedActivityView):
            raise UntrustedInstanceEvidenceError
        if not source.high_stakes_eligible:
            raise UntrustedInstanceEvidenceError
        return super().evaluate_evidence(state_token=state_token, verdict=verdict)


__all__ = [
    "BlueprintLearningPlanService",
    "BlueprintTrustError",
    "UntrustedInstanceEvidenceError",
]
