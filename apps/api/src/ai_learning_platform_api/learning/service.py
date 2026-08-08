"""Deterministic adaptive planning and learner-attested evidence history."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_learning_platform_api.learning.assessment import AssessmentCalibrationEngine
from ai_learning_platform_api.learning.catalog import (
    ROLE_CATALOG,
    CompetencyDefinition,
    RoleDefinition,
)
from ai_learning_platform_api.learning.evidence import apply_trusted_verdict
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    AssessmentAttemptView,
    AssessmentStartRequest,
    AssessmentSubmissionView,
    AssessmentSubmitRequest,
    CompetencyEvidenceState,
    CompetencyView,
    EvidenceRecordView,
    LearnerState,
    PlanRequest,
    PlanView,
    PriorityCompetencyView,
    ProgressRequest,
    ReplanRequest,
    RoleView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.targeting import default_target_for, resolve_target

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]

_MAX_EVIDENCE_HISTORY = 24
_MAX_ASSESSMENT_HISTORY = 12
_MAX_COMPLETED_IDS = 128
_REVIEW_INTERVAL_DAYS = {0: 1, 1: 2, 2: 4, 3: 7, 4: 14}


class LearningPlanError(ValueError):
    """Base class for safe product-domain failures."""

    code = "LEARNING_PLAN_ERROR"


class InvalidStateTokenError(LearningPlanError):
    """The browser-provided signed state is malformed or has been modified."""

    code = "INVALID_STATE_TOKEN"


class UnknownRoleError(LearningPlanError):
    """The requested target role is not in the versioned catalog."""

    code = "UNKNOWN_TARGET_ROLE"


class InvalidRatingError(LearningPlanError):
    """The diagnosis contains duplicate or unknown competency ratings."""

    code = "INVALID_COMPETENCY_RATING"


class UnknownActivityError(LearningPlanError):
    """The requested activity does not belong to the signed learner state."""

    code = "UNKNOWN_ACTIVITY"


class ActivityAlreadyCompletedError(LearningPlanError):
    """The requested activity was already accepted in the signed state."""

    code = "ACTIVITY_ALREADY_COMPLETED"


class InvalidEvidenceError(LearningPlanError):
    """The evidence submission contains duplicate or unknown acceptance criteria."""

    code = "INVALID_EVIDENCE"


class InvalidFocusError(LearningPlanError):
    """The requested replan focus contains duplicate or unknown competencies."""

    code = "INVALID_REPLAN_FOCUS"


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise InvalidStateTokenError from error
    if _urlsafe_encode(decoded) != value:
        raise InvalidStateTokenError
    return decoded


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidStateTokenError from error
    if parsed.tzinfo is None:
        raise InvalidStateTokenError
    return parsed.astimezone(UTC)


class SignedStateCodec:
    """Canonical HMAC codec for browser-carried learner state."""

    def __init__(self, secret: str) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("learner state secret must contain at least 32 UTF-8 bytes")
        self._secret = secret.encode("utf-8")

    def encode(self, state: LearnerState) -> str:
        payload = json.dumps(
            state.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._secret, payload, hashlib.sha256).digest()
        return f"{_urlsafe_encode(payload)}.{_urlsafe_encode(signature)}"

    def decode(self, token: str) -> LearnerState:
        if len(token) > 65_536 or token.count(".") != 1:
            raise InvalidStateTokenError
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        payload = _urlsafe_decode(encoded_payload)
        signature = _urlsafe_decode(encoded_signature)
        expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidStateTokenError
        try:
            decoded = json.loads(payload)
            return LearnerState.model_validate(decoded)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
            raise InvalidStateTokenError from error


class LearningPlanService:
    """Create, advance, and replan deterministic learner-specific planning hypotheses."""

    def __init__(
        self,
        secret: str,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory | None = None,
    ) -> None:
        self._codec = SignedStateCodec(secret)
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)
        self._id_factory = id_factory if id_factory is not None else uuid4
        self._assessment = AssessmentCalibrationEngine(
            secret, clock=self._clock, id_factory=self._id_factory
        )

    def list_roles(self) -> list[RoleView]:
        """Return versioned role candidates with explicit provisional Target defaults."""
        return [self._role_view(role) for role in ROLE_CATALOG.values()]

    def create_plan(self, request: PlanRequest) -> PlanView:
        """Resolve the Target, record self-report as planning input, and generate bounded work."""
        role = ROLE_CATALOG.get(request.target_role)
        if role is None:
            raise UnknownRoleError

        target = resolve_target(role, request.target)
        rating_map = self._rating_map(role, request)
        planning_signal = {
            competency.identifier: rating_map.get(competency.identifier, 0) * 25
            for competency in role.competencies
        }
        seed = self._learner_seed(
            request.learner_name,
            request.target_role,
            request.experience_summary,
        )
        activities = self._generate_build_activities(
            role=role,
            planning_signal=planning_signal,
            weekly_hours=request.weekly_hours,
            focus_competency_ids=[],
            learner_name=request.learner_name.strip(),
            experience_summary=request.experience_summary.strip(),
            seed=seed,
            generation=0,
        )
        state = LearnerState(
            schema_version=5,
            learner_id=str(self._id_factory()),
            learner_name=request.learner_name.strip(),
            target_role=request.target_role,
            target=target,
            weekly_hours=request.weekly_hours,
            experience_summary=request.experience_summary.strip(),
            created_at=self._now().isoformat(),
            sequence=0,
            planning_signal=planning_signal,
            mastery={},
            completed_activity_ids=[],
            activities=activities,
            plan_revision=0,
            focus_competency_ids=[],
            evidence_history=[],
            competency_evidence={
                item.identifier: CompetencyEvidenceState(competency_id=item.identifier)
                for item in role.competencies
            },
        )
        return self._project(state, role)

    def resume(self, state_token: str) -> PlanView:
        """Verify, upgrade, and project a previously issued learner state."""
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        return self._project(self._upgrade_state(state, role), role)

    def start_assessment(self, request: AssessmentStartRequest) -> AssessmentAttemptView:
        """Issue an expiring calibration attempt for current planning priorities."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        diagnostic_signal = self._diagnostic_signal_values(
            role, state.planning_signal, state.assessment_scores
        )
        priorities = self._rank_competencies(
            role,
            diagnostic_signal,
            state.focus_competency_ids,
        )[: request.question_count]
        return self._assessment.start(
            state=state,
            role=role,
            competency_ids=[item.identifier for item in priorities],
        )

    def submit_assessment(self, request: AssessmentSubmitRequest) -> AssessmentSubmissionView:
        """Score a calibration attempt and regenerate diagnostic-informed work."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        outcome = self._assessment.score(state=state, role=role, request=request)
        assessment_scores = dict(state.assessment_scores)
        assessment_scores.update(outcome.competency_scores)
        diagnostic_signal = self._diagnostic_signal_values(
            role, state.planning_signal, assessment_scores
        )
        revision = state.plan_revision + 1
        pending_reviews = [
            activity
            for activity in state.activities
            if activity.kind == "review" and activity.id not in state.completed_activity_ids
        ]
        build_activities = self._generate_build_activities(
            role=role,
            planning_signal=diagnostic_signal,
            weekly_hours=state.weekly_hours,
            focus_competency_ids=state.focus_competency_ids,
            learner_name=state.learner_name,
            experience_summary=state.experience_summary,
            seed=self._learner_seed(
                state.learner_name,
                state.target_role,
                f"{state.experience_summary}|assessment:{outcome.record.attempt_id}",
            ),
            generation=revision,
        )
        updated = state.model_copy(
            update={
                "schema_version": 5,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "assessment_scores": assessment_scores,
                "assessment_history": [*state.assessment_history, outcome.record][
                    -_MAX_ASSESSMENT_HISTORY:
                ],
                "activities": [*pending_reviews, *build_activities],
            }
        )
        plan = self._project(updated, role)
        return AssessmentSubmissionView(
            score_percent=outcome.record.score_percent,
            correct_count=outcome.record.correct_count,
            total_count=outcome.record.total_count,
            feedback=list(outcome.feedback),
            plan=plan,
        )

    def complete_activity(self, request: ProgressRequest) -> PlanView:
        """Record learner-attested work without promoting it to verified mastery."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        activity = next((item for item in state.activities if item.id == request.activity_id), None)
        if activity is None:
            raise UnknownActivityError
        if activity.id in state.completed_activity_ids:
            raise ActivityAlreadyCompletedError

        criteria_met = self._validated_criteria(activity, request.criteria_met)
        now = self._now()
        delta = self._planning_signal_delta(
            criteria_met=len(criteria_met),
            criteria_total=len(activity.acceptance_criteria),
            confidence=request.confidence,
            reflection=request.reflection,
        )
        review_at = now + timedelta(days=_REVIEW_INTERVAL_DAYS[request.confidence])
        completed = [*state.completed_activity_ids, activity.id][-_MAX_COMPLETED_IDS:]
        planning_signal = dict(state.planning_signal)
        planning_signal[activity.competency_id] = min(
            100,
            planning_signal.get(activity.competency_id, 0) + delta,
        )
        evidence = EvidenceRecordView(
            evidence_id=self._evidence_id(
                state.learner_id,
                activity.id,
                now.isoformat(),
            ),
            activity_id=activity.id,
            competency_id=activity.competency_id,
            competency_name=activity.competency_name,
            title=activity.title,
            submitted_at=now.isoformat(),
            reflection=request.reflection.strip(),
            evidence_reference=request.evidence_reference.strip(),
            criteria_met=criteria_met,
            confidence=request.confidence,
            source="learner_attested",
            disposition="recorded",
            independence="unverified",
            assistance="unknown",
            reasoning="submitted" if request.reflection.strip() else "not_observed",
            planning_signal_delta=delta,
            next_review_at=review_at.isoformat(),
        )
        review_activity = self._review_activity(
            source=activity,
            learner_name=state.learner_name,
            generation=state.sequence + 1,
            available_from=review_at,
        )
        activities = [*state.activities, review_activity]
        updated = state.model_copy(
            update={
                "schema_version": 5,
                "sequence": state.sequence + 1,
                "planning_signal": planning_signal,
                "mastery": {},
                "completed_activity_ids": completed,
                "activities": activities,
                "evidence_history": [*state.evidence_history, evidence][-_MAX_EVIDENCE_HISTORY:],
            }
        )
        return self._project(updated, role)

    def evaluate_evidence(
        self,
        *,
        state_token: str,
        verdict: TrustedEvidenceVerdict,
    ) -> PlanView:
        """Apply one server-side trusted verdict without granting readiness."""
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        transition = apply_trusted_verdict(
            state=state,
            verdict=verdict,
            occurred_at=self._now(),
        )
        if not transition.changed:
            return self._project(state, role)
        updated = transition.state.model_copy(
            update={
                "schema_version": 5,
                "sequence": state.sequence + 1,
            }
        )
        return self._project(updated, role)

    def replan(self, request: ReplanRequest) -> PlanView:
        """Regenerate active work while preserving recorded planning inputs and reviews."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        focus = self._validated_focus(role, request.focus_competency_ids)
        revision = state.plan_revision + 1
        seed = self._learner_seed(
            state.learner_name,
            state.target_role,
            f"{state.experience_summary}|revision:{revision}",
        )
        pending_reviews = [
            activity
            for activity in state.activities
            if activity.kind == "review" and activity.id not in state.completed_activity_ids
        ]
        build_activities = self._generate_build_activities(
            role=role,
            planning_signal=self._diagnostic_signal_values(
                role, state.planning_signal, state.assessment_scores
            ),
            weekly_hours=request.weekly_hours,
            focus_competency_ids=focus,
            learner_name=state.learner_name,
            experience_summary=state.experience_summary,
            seed=seed,
            generation=revision,
        )
        updated = state.model_copy(
            update={
                "schema_version": 5,
                "weekly_hours": request.weekly_hours,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "focus_competency_ids": focus,
                "activities": [*pending_reviews, *build_activities],
            }
        )
        return self._project(updated, role)

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
        state = self._upgrade_state(state, role)
        now = self._now()
        completed = set(state.completed_activity_ids)
        available = [
            activity
            for activity in state.activities
            if activity.id not in completed and self._is_available(activity, now)
        ]
        available.sort(
            key=lambda item: (
                0 if item.kind == "review" else 1,
                item.available_from or "",
            )
        )
        current = available[0] if available else None
        diagnostic_signal = self._diagnostic_signal_values(
            role, state.planning_signal, state.assessment_scores
        )
        priorities = self._rank_competencies(
            role,
            diagnostic_signal,
            state.focus_competency_ids,
        )[:4]
        total_weight = sum(item.weight for item in role.competencies)
        weighted_planning = sum(
            state.planning_signal.get(item.identifier, 0) * item.weight
            for item in role.competencies
        )
        weighted_diagnostic = sum(
            diagnostic_signal.get(item.identifier, 0) * item.weight for item in role.competencies
        )
        planning_signal_percent = round(weighted_planning / total_weight)
        diagnostic_signal_percent = round(weighted_diagnostic / total_weight)
        assessment_coverage = round((len(state.assessment_scores) / len(role.competencies)) * 100)
        future_reviews = sorted(
            _parse_timestamp(activity.available_from)
            for activity in state.activities
            if activity.kind == "review"
            and activity.id not in completed
            and activity.available_from is not None
            and _parse_timestamp(activity.available_from) > now
        )
        evidence_review_dates = sorted(
            _parse_timestamp(item.due_at)
            for item in state.review_state.values()
            if _parse_timestamp(item.due_at) > now
        )
        all_review_dates = sorted([*future_reviews, *evidence_review_dates])
        current_completed = sum(1 for item in state.activities if item.id in completed)
        assert state.target is not None
        return PlanView(
            state_token=self._codec.encode(state),
            learner_id=state.learner_id,
            learner_name=state.learner_name,
            role=self._role_view(role),
            target=state.target,
            claim_state="validation_locked",
            verified_readiness_percent=None,
            planning_signal_percent=planning_signal_percent,
            diagnostic_signal_percent=diagnostic_signal_percent,
            assessment_coverage_percent=assessment_coverage,
            priority_competencies=[
                PriorityCompetencyView(
                    id=item.identifier,
                    name=item.name,
                    category=item.category,
                    planning_signal_percent=state.planning_signal.get(item.identifier, 0),
                    diagnostic_signal_percent=diagnostic_signal.get(item.identifier, 0),
                    assessment_percent=state.assessment_scores.get(item.identifier),
                    priority_gap_percent=100 - diagnostic_signal.get(item.identifier, 0),
                    evidence_status=state.competency_evidence[item.identifier].status,
                    focused=item.identifier in state.focus_competency_ids,
                )
                for item in priorities
            ],
            competency_evidence=[
                state.competency_evidence[item.identifier] for item in role.competencies
            ],
            evidence_evaluations=list(state.evidence_evaluations[-24:]),
            active_misconceptions=[
                item for item in state.misconceptions if item.status == "active"
            ],
            review_state=sorted(
                state.review_state.values(),
                key=lambda item: (item.due_at, item.competency_id),
            ),
            current_activity=current,
            completed_count=current_completed,
            total_count=len(state.activities),
            sequence=state.sequence,
            weekly_hours=state.weekly_hours,
            plan_revision=state.plan_revision,
            focus_competency_ids=list(state.focus_competency_ids),
            evidence_history=list(state.evidence_history[-12:]),
            assessment_history=list(state.assessment_history[-8:]),
            next_review_at=all_review_dates[0].isoformat() if all_review_dates else None,
        )

    @staticmethod
    def _diagnostic_signal_values(
        role: RoleDefinition,
        planning_signal: dict[str, int],
        assessment_scores: dict[str, int],
    ) -> dict[str, int]:
        """Blend planning and calibration only for prioritization."""
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

    def _generate_build_activities(
        self,
        *,
        role: RoleDefinition,
        planning_signal: dict[str, int],
        weekly_hours: int,
        focus_competency_ids: list[str],
        learner_name: str,
        experience_summary: str,
        seed: str,
        generation: int,
    ) -> list[ActivityView]:
        ranked = self._rank_competencies(role, planning_signal, focus_competency_ids)
        activity_count = min(len(ranked), max(4, weekly_hours // 2))
        return [
            self._activity_view(
                role=role,
                competency=competency,
                seed=seed,
                position=position,
                learner_name=learner_name,
                experience_summary=experience_summary,
                generation=generation,
                planning_signal=planning_signal.get(competency.identifier, 0),
                focused=competency.identifier in focus_competency_ids,
            )
            for position, competency in enumerate(ranked[:activity_count], start=1)
        ]

    @staticmethod
    def _rating_map(role: RoleDefinition, request: PlanRequest) -> dict[str, int]:
        ratings: dict[str, int] = {}
        known_ids = {competency.identifier for competency in role.competencies}
        for rating in request.ratings:
            if rating.competency_id not in known_ids or rating.competency_id in ratings:
                raise InvalidRatingError
            ratings[rating.competency_id] = rating.score
        return ratings

    @staticmethod
    def _validated_criteria(activity: ActivityView, submitted: list[str]) -> list[str]:
        if len(submitted) != len(set(submitted)):
            raise InvalidEvidenceError
        allowed = set(activity.acceptance_criteria)
        if any(criterion not in allowed for criterion in submitted):
            raise InvalidEvidenceError
        return list(submitted)

    @staticmethod
    def _validated_focus(role: RoleDefinition, submitted: list[str]) -> list[str]:
        if len(submitted) != len(set(submitted)):
            raise InvalidFocusError
        known = {competency.identifier for competency in role.competencies}
        if any(identifier not in known for identifier in submitted):
            raise InvalidFocusError
        return list(submitted)

    @staticmethod
    def _planning_signal_delta(
        *,
        criteria_met: int,
        criteria_total: int,
        confidence: int,
        reflection: str,
    ) -> int:
        """Weight learner-attested completion only as a future-diagnosis planning signal."""
        ratio = criteria_met / max(criteria_total, 1)
        reflection_bonus = 4 if len(reflection.strip()) >= 80 else 0
        return min(25, 5 + round(10 * ratio) + (confidence * 2) + reflection_bonus)

    @staticmethod
    def _rank_competencies(
        role: RoleDefinition,
        planning_signal: dict[str, int],
        focus_competency_ids: list[str],
    ) -> list[CompetencyDefinition]:
        focus_order = {
            identifier: position for position, identifier in enumerate(focus_competency_ids)
        }
        return sorted(
            role.competencies,
            key=lambda item: (
                0 if item.identifier in focus_order else 1,
                focus_order.get(item.identifier, len(focus_order)),
                -(100 - planning_signal.get(item.identifier, 0)) * item.weight,
                item.identifier,
            ),
        )

    @staticmethod
    def _evidence_id(learner_id: str, activity_id: str, submitted_at: str) -> str:
        digest = hashlib.sha256(f"{learner_id}|{activity_id}|{submitted_at}".encode()).hexdigest()[
            :24
        ]
        return f"evidence-{digest}"

    @staticmethod
    def _learner_seed(learner_name: str, target_role: str, context: str) -> str:
        return hashlib.sha256(
            "|".join(
                (
                    learner_name.casefold().strip(),
                    target_role,
                    context.casefold().strip(),
                )
            ).encode("utf-8")
        ).hexdigest()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("learning plan clock must return a timezone-aware datetime")
        return value.astimezone(UTC)

    @staticmethod
    def _is_available(activity: ActivityView, now: datetime) -> bool:
        return activity.available_from is None or _parse_timestamp(activity.available_from) <= now

    @classmethod
    def _upgrade_state(cls, state: LearnerState, role: RoleDefinition) -> LearnerState:
        """Migrate legacy signed state into schema v5 without inventing trusted evidence."""
        planning_signal = (
            dict(state.planning_signal) if state.planning_signal else dict(state.mastery)
        )
        target = state.target if state.target is not None else default_target_for(role)
        evidence_history = [
            item
            if item.evidence_id
            else item.model_copy(
                update={
                    "evidence_id": cls._evidence_id(
                        state.learner_id,
                        item.activity_id,
                        item.submitted_at,
                    )
                }
            )
            for item in state.evidence_history
        ]
        competency_evidence = {
            item.identifier: state.competency_evidence.get(
                item.identifier,
                CompetencyEvidenceState(competency_id=item.identifier),
            )
            for item in role.competencies
        }
        return state.model_copy(
            update={
                "schema_version": 5,
                "target": target,
                "planning_signal": planning_signal,
                "mastery": {},
                "evidence_history": evidence_history,
                "competency_evidence": competency_evidence,
            }
        )

    @staticmethod
    def _role_view(role: RoleDefinition) -> RoleView:
        return RoleView(
            id=role.identifier,
            version=role.version,
            title=role.title,
            summary=role.summary,
            validation_state="provisional",
            default_target=default_target_for(role),
            competencies=[
                CompetencyView(
                    id=item.identifier,
                    name=item.name,
                    category=item.category,
                    description=item.description,
                    weight=item.weight,
                )
                for item in role.competencies
            ],
        )

    @staticmethod
    def _activity_view(
        *,
        role: RoleDefinition,
        competency: CompetencyDefinition,
        seed: str,
        position: int,
        learner_name: str,
        experience_summary: str,
        generation: int,
        planning_signal: int,
        focused: bool,
    ) -> ActivityView:
        selector_seed = hashlib.sha256(
            f"{seed}|{competency.identifier}|{position}|{generation}".encode()
        ).hexdigest()
        template = competency.activities[int(selector_seed[:4], 16) % len(competency.activities)]
        fingerprint = selector_seed[:12]
        context = experience_summary or "current self-report and resolved target"
        focus_reason = " It was explicitly selected as a focus area." if focused else ""
        return ActivityView(
            id=f"activity-build-{competency.identifier}-{fingerprint}",
            competency_id=competency.identifier,
            competency_name=competency.name,
            title=f"{position:02d}. {template.title}",
            objective=(
                f"{template.objective} Personalize the decisions for {learner_name} using their "
                f"stated context: {context}."
            ),
            deliverable=template.deliverable,
            acceptance_criteria=list(template.acceptance_criteria),
            estimated_minutes=template.estimated_minutes,
            kind="build",
            rationale=(
                f"Selected from provisional role profile {role.version} because the current "
                f"planning signal is {planning_signal}% and the competency weight is "
                f"{competency.weight}.{focus_reason} This signal prioritizes diagnosis/work; "
                "it is not verified mastery."
            ),
            generation=generation,
            available_from=None,
        )

    @staticmethod
    def _review_activity(
        *,
        source: ActivityView,
        learner_name: str,
        generation: int,
        available_from: datetime,
    ) -> ActivityView:
        fingerprint = hashlib.sha256(
            f"{source.id}|review|{generation}|{available_from.isoformat()}".encode()
        ).hexdigest()[:12]
        return ActivityView(
            id=f"activity-review-{source.competency_id}-{fingerprint}",
            competency_id=source.competency_id,
            competency_name=source.competency_name,
            title=f"Review · {source.title.removeprefix('Review · ')}",
            objective=(
                f"Reproduce or critique the earlier work for {learner_name} without relying on "
                "the original step-by-step notes, then identify what still requires support."
            ),
            deliverable=(
                "A concise reproduction or review note linked to the earlier deliverable, with "
                "any regression, misconception, or improvement recorded."
            ),
            acceptance_criteria=list(source.acceptance_criteria),
            estimated_minutes=max(30, source.estimated_minutes // 2),
            kind="review",
            rationale=(
                "Scheduled as a spaced retrieval review from a learner-attested work cycle. "
                "Completion remains a planning signal until independent evidence gates exist."
            ),
            generation=generation,
            available_from=available_from.isoformat(),
        )