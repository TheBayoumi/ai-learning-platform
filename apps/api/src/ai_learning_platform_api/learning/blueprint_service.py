"""G05 service extension that binds approved catalog blueprints to learner-specific instances."""

from __future__ import annotations

import hashlib
from datetime import datetime

from ai_learning_platform_api.learning.blueprints import (
    BlueprintTrustError,
    CollisionHistoryEntry,
    attach_blueprint_identity,
    bind_learner_instance,
    exposure_from_activity,
)
from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.planner import (
    CurriculumDecision,
    plan_version_id,
    target_fingerprint,
)
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CurriculumTrigger,
    LearnerPlanVersion,
    LearnerState,
    PlanView,
    ProgressRequest,
    TargetView,
    TaskExposureView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanError
from ai_learning_platform_api.learning.service import (
    LearningPlanService as BaseLearningPlanService,
)

_MAX_TASK_EXPOSURES = 16
_MAX_PLAN_VERSIONS = 3


class UntrustedInstanceEvidenceError(LearningPlanError):
    """Trusted evaluator evidence cannot be accepted from an untrusted generated instance."""

    code = "UNTRUSTED_TASK_INSTANCE"


class EvidenceRubricMismatchError(LearningPlanError):
    """Trusted evaluator verdict names a rubric other than the served task rubric."""

    code = "EVIDENCE_RUBRIC_MISMATCH"


class EvidenceInstanceContractMismatchError(LearningPlanError):
    """Trusted evaluator verdict does not attest to the exact learner-specific task contract."""

    code = "EVIDENCE_INSTANCE_CONTRACT_MISMATCH"


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
    ) -> ActivityView:
        base = BaseLearningPlanService._activity_view(
            role=role,
            decision=decision,
            seed=seed,
            position=position,
            learner_name=learner_name,
            experience_summary=experience_summary,
            generation=generation,
        )
        return attach_blueprint_identity(role=role, activity=base)

    @staticmethod
    def _review_activity(
        *,
        source: ActivityView,
        learner_name: str,
        generation: int,
        available_from: datetime,
    ) -> ActivityView:
        review = BaseLearningPlanService._review_activity(
            source=source,
            learner_name=learner_name,
            generation=generation,
            available_from=available_from,
        )
        seed = hashlib.sha256(
            f"review|{source.id}|{generation}|{available_from.isoformat()}".encode()
        ).hexdigest()[:32]
        semantic_tokens = [
            f"r:{hashlib.sha256(source.blueprint_id.encode()).hexdigest()[:8]}",
            f"s:{source.semantic_fingerprint[:8]}",
        ]
        return review.model_copy(
            update={
                "item_family_id": source.item_family_id,
                "item_family_version": source.item_family_version,
                "item_family_trust": source.item_family_trust,
                "blueprint_id": source.blueprint_id,
                "blueprint_version": source.blueprint_version,
                "blueprint_trust": source.blueprint_trust,
                "blueprint_approval_id": source.blueprint_approval_id,
                "blueprint_approved_by": source.blueprint_approved_by,
                "blueprint_approval_version": source.blueprint_approval_version,
                "rubric_version": source.rubric_version,
                "instance_seed": seed,
                "semantic_fingerprint": hashlib.sha256(
                    f"review|{source.semantic_fingerprint}|{generation}".encode()
                ).hexdigest()[:24],
                "semantic_signature": hashlib.sha256("|".join(semantic_tokens).encode()).hexdigest()[
                    :24
                ],
                "semantic_tokens": semantic_tokens,
                "scenario_tags": ["review", f"g:{generation}"],
                "instance_requirements": [],
                "instance_contract_hash": "",
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
    ) -> LearnerPlanVersion:
        prior_exposures = list(previous.task_exposures) if previous is not None else []
        target_hash = target_fingerprint(target)
        bound: list[ActivityView] = []
        collision_scope: list[CollisionHistoryEntry] = list(prior_exposures)
        for position, raw_activity in enumerate(activities, start=1):
            activity = raw_activity
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
                        semantic_signature=activity.semantic_signature,
                        semantic_tokens=list(activity.semantic_tokens),
                        instance_contract_hash=activity.instance_contract_hash,
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
        current_plan_version_id = base_version.plan_version_id
        finalized = [
            activity.model_copy(update={"plan_version_id": current_plan_version_id})
            for activity in bound
        ]
        activities[:] = finalized
        current_exposures = [
            exposure_from_activity(
                activity=activity,
                plan_version_id=current_plan_version_id,
                served_at=created_at.isoformat(),
            )
            for activity in finalized
            if activity.kind == "build" and activity.instance_seed and activity.semantic_fingerprint
        ]
        # Browser-carried history is only a bounded replay/cache window. Durable production
        # uniqueness is enforced by the unlinkable PostgreSQL collision-fingerprint index.
        exposure_history = [*prior_exposures, *current_exposures][-_MAX_TASK_EXPOSURES:]
        return base_version.model_copy(
            update={"activities": finalized, "task_exposures": exposure_history}
        )

    @staticmethod
    def _append_plan_version(
        state: LearnerState,
        version: LearnerPlanVersion,
    ) -> list[LearnerPlanVersion]:
        """Keep immutable curriculum snapshots while avoiding cumulative ledger duplication."""
        archived = [item.model_copy(update={"task_exposures": []}) for item in state.plan_versions]
        return [*archived, version][-_MAX_PLAN_VERSIONS:]

    def complete_activity(self, request: ProgressRequest) -> PlanView:
        """Bind learner evidence to the exact approved rubric and enforceable instance contract."""
        before = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(before.target_role)
        if role is None:
            raise LearningPlanError
        before = self._upgrade_state(before, role)
        source = next((item for item in before.activities if item.id == request.activity_id), None)
        if source is None:
            return super().complete_activity(request)

        projected = super().complete_activity(request)
        state = self._codec.decode(projected.state_token)
        if not state.evidence_history:
            return projected
        evidence = state.evidence_history[-1]
        fully_satisfied = (
            len(evidence.criteria_met) == len(source.acceptance_criteria)
            and set(evidence.criteria_met) == set(source.acceptance_criteria)
        )
        trusted_source = bool(
            source.high_stakes_eligible
            and source.blueprint_approval_id
            and source.instance_contract_hash
            and fully_satisfied
        )
        hardened = evidence.model_copy(
            update={
                "source_blueprint_approval_id": source.blueprint_approval_id,
                "source_instance_contract_hash": source.instance_contract_hash,
                "source_high_stakes_eligible": trusted_source,
            }
        )
        updated = state.model_copy(
            update={"evidence_history": [*state.evidence_history[:-1], hardened]}
        )
        return self._project(updated, role)

    def rebind_external_exposures(
        self,
        *,
        state_token: str,
        external_exposures: tuple[CollisionHistoryEntry, ...],
    ) -> PlanView:
        """Rebind active builds against durable cohort history without losing state semantics."""
        if not external_exposures:
            return self.resume(state_token)
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise LearningPlanError
        state = self._upgrade_state(state, role)
        active = self._active_plan_version(state)
        target = state.target
        if active is None or target is None:
            raise LearningPlanError
        previous_id = active.delta.previous_plan_version_id
        previous = None
        if previous_id is not None:
            previous = next(
                (item for item in state.plan_versions if item.plan_version_id == previous_id),
                None,
            )
            if previous is None:
                raise LearningPlanError

        prior_exposures = [
            item for item in active.task_exposures if item.plan_version_id != active.plan_version_id
        ]
        collision_scope: list[CollisionHistoryEntry] = [*external_exposures, *prior_exposures]
        rebound: list[ActivityView] = []
        for position, activity in enumerate(active.activities, start=1):
            candidate = activity
            if activity.kind == "build":
                candidate = bind_learner_instance(
                    role=role,
                    activity=activity,
                    learner_id=state.learner_id,
                    target_fingerprint=target_fingerprint(target),
                    revision=active.revision,
                    position=position,
                    exposures=collision_scope,
                )
                collision_scope.append(
                    exposure_from_activity(
                        activity=candidate,
                        plan_version_id="pending",
                        served_at=active.created_at,
                    )
                )
            rebound.append(candidate)
        next_id = plan_version_id(
            learner_id=state.learner_id,
            role_version=role.version,
            revision=active.revision,
            target_hash=active.target_fingerprint,
            trigger=active.trigger,
            activity_ids=[item.id for item in rebound],
            priority_ids=[item.competency_id for item in active.priorities],
        )
        finalized = [item.model_copy(update={"plan_version_id": next_id}) for item in rebound]
        current_exposures = [
            exposure_from_activity(
                activity=item,
                plan_version_id=next_id,
                served_at=active.created_at,
            )
            for item in finalized
            if item.kind == "build"
        ]
        delta = self._plan_delta(previous, finalized, active.priorities, active.trigger)
        updated_version = active.model_copy(
            update={
                "plan_version_id": next_id,
                "activities": finalized,
                "delta": delta,
                "task_exposures": [*prior_exposures, *current_exposures][-_MAX_TASK_EXPOSURES:],
            }
        )
        versions = [
            updated_version if item.plan_version_id == active.plan_version_id else item
            for item in state.plan_versions
        ]
        active_activity_ids = {item.id for item in active.activities}
        external_state_activities = [
            item for item in state.activities if item.id not in active_activity_ids
        ]
        updated_state = state.model_copy(
            update={
                "activities": [*external_state_activities, *finalized],
                "plan_versions": versions,
                "active_plan_version_id": next_id,
            }
        )
        return self._project(updated_state, role)

    def evaluate_evidence(
        self,
        *,
        state_token: str,
        verdict: TrustedEvidenceVerdict,
    ) -> PlanView:
        """Require immutable approval provenance and exact rubric/instance attestation."""
        state = self._codec.decode(state_token)
        evidence = next(
            (item for item in state.evidence_history if item.evidence_id == verdict.evidence_id),
            None,
        )
        if evidence is None:
            return super().evaluate_evidence(state_token=state_token, verdict=verdict)
        if not evidence.source_high_stakes_eligible:
            raise UntrustedInstanceEvidenceError
        if (
            not evidence.source_blueprint_id
            or not evidence.source_blueprint_approval_id
            or not evidence.source_rubric_version
            or not evidence.source_instance_contract_hash
        ):
            raise UntrustedInstanceEvidenceError
        if verdict.rubric_version != evidence.source_rubric_version:
            raise EvidenceRubricMismatchError
        if verdict.instance_contract_hash != evidence.source_instance_contract_hash:
            raise EvidenceInstanceContractMismatchError
        return super().evaluate_evidence(state_token=state_token, verdict=verdict)


__all__ = [
    "BlueprintLearningPlanService",
    "BlueprintTrustError",
    "EvidenceInstanceContractMismatchError",
    "EvidenceRubricMismatchError",
    "UntrustedInstanceEvidenceError",
]
