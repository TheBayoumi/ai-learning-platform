"""Deterministic adaptive curriculum, evidence history, and signed learner state."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_learning_platform_api.learning.catalog import (
    ROLE_CATALOG,
    CompetencyDefinition,
    RoleDefinition,
)
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CompetencyView,
    EvidenceRecordView,
    LearnerState,
    PlanRequest,
    PlanView,
    PriorityCompetencyView,
    ProgressRequest,
    ReplanRequest,
    RoleView,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]

_MAX_EVIDENCE_HISTORY = 24
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
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise InvalidStateTokenError from error


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
    """Create, advance, and replan deterministic learner curricula."""

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

    def list_roles(self) -> list[RoleView]:
        """Return the versioned role catalog exposed by this product slice."""
        return [self._role_view(role) for role in ROLE_CATALOG.values()]

    def create_plan(self, request: PlanRequest) -> PlanView:
        """Diagnose current gaps and generate learner-unique bounded work."""
        role = ROLE_CATALOG.get(request.target_role)
        if role is None:
            raise UnknownRoleError

        rating_map = self._rating_map(role, request)
        mastery = {
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
            mastery=mastery,
            weekly_hours=request.weekly_hours,
            focus_competency_ids=[],
            learner_name=request.learner_name.strip(),
            experience_summary=request.experience_summary.strip(),
            seed=seed,
            generation=0,
        )
        state = LearnerState(
            schema_version=2,
            learner_id=str(self._id_factory()),
            learner_name=request.learner_name.strip(),
            target_role=request.target_role,
            weekly_hours=request.weekly_hours,
            experience_summary=request.experience_summary.strip(),
            created_at=self._now().isoformat(),
            sequence=0,
            mastery=mastery,
            completed_activity_ids=[],
            activities=activities,
            plan_revision=0,
            focus_competency_ids=[],
            evidence_history=[],
        )
        return self._project(state, role)

    def resume(self, state_token: str) -> PlanView:
        """Verify and project a previously issued learner state."""
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        return self._project(state, role)

    def complete_activity(self, request: ProgressRequest) -> PlanView:
        """Record learner-attested evidence and schedule a spaced review."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        activity = next((item for item in state.activities if item.id == request.activity_id), None)
        if activity is None:
            raise UnknownActivityError
        if activity.id in state.completed_activity_ids:
            raise ActivityAlreadyCompletedError

        criteria_met = self._validated_criteria(activity, request.criteria_met)
        now = self._now()
        delta = self._provisional_mastery_delta(
            criteria_met=len(criteria_met),
            criteria_total=len(activity.acceptance_criteria),
            confidence=request.confidence,
            reflection=request.reflection,
        )
        review_at = now + timedelta(days=_REVIEW_INTERVAL_DAYS[request.confidence])
        completed = [*state.completed_activity_ids, activity.id][-_MAX_COMPLETED_IDS:]
        mastery = dict(state.mastery)
        mastery[activity.competency_id] = min(
            100,
            mastery.get(activity.competency_id, 0) + delta,
        )
        evidence = EvidenceRecordView(
            activity_id=activity.id,
            competency_id=activity.competency_id,
            competency_name=activity.competency_name,
            title=activity.title,
            submitted_at=now.isoformat(),
            reflection=request.reflection.strip(),
            evidence_reference=request.evidence_reference.strip(),
            criteria_met=criteria_met,
            confidence=request.confidence,
            provisional_mastery_delta=delta,
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
                "schema_version": 2,
                "sequence": state.sequence + 1,
                "mastery": mastery,
                "completed_activity_ids": completed,
                "activities": activities,
                "evidence_history": [*state.evidence_history, evidence][-_MAX_EVIDENCE_HISTORY:],
            }
        )
        return self._project(updated, role)

    def replan(self, request: ReplanRequest) -> PlanView:
        """Regenerate active build work while preserving evidence and pending reviews."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
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
            mastery=state.mastery,
            weekly_hours=request.weekly_hours,
            focus_competency_ids=focus,
            learner_name=state.learner_name,
            experience_summary=state.experience_summary,
            seed=seed,
            generation=revision,
        )
        updated = state.model_copy(
            update={
                "schema_version": 2,
                "weekly_hours": request.weekly_hours,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "focus_competency_ids": focus,
                "activities": [*pending_reviews, *build_activities],
            }
        )
        return self._project(updated, role)

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
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
        priorities = self._rank_competencies(
            role,
            state.mastery,
            state.focus_competency_ids,
        )[:4]
        total_weight = sum(item.weight for item in role.competencies)
        weighted_mastery = sum(
            state.mastery.get(item.identifier, 0) * item.weight for item in role.competencies
        )
        readiness = round(weighted_mastery / total_weight)
        future_reviews = sorted(
            _parse_timestamp(activity.available_from)
            for activity in state.activities
            if activity.kind == "review"
            and activity.id not in completed
            and activity.available_from is not None
            and _parse_timestamp(activity.available_from) > now
        )
        current_completed = sum(1 for item in state.activities if item.id in completed)
        return PlanView(
            state_token=self._codec.encode(state),
            learner_id=state.learner_id,
            learner_name=state.learner_name,
            role=self._role_view(role),
            readiness_percent=readiness,
            priority_competencies=[
                PriorityCompetencyView(
                    id=item.identifier,
                    name=item.name,
                    category=item.category,
                    mastery_percent=state.mastery.get(item.identifier, 0),
                    gap_percent=100 - state.mastery.get(item.identifier, 0),
                    focused=item.identifier in state.focus_competency_ids,
                )
                for item in priorities
            ],
            current_activity=current,
            completed_count=current_completed,
            total_count=len(state.activities),
            sequence=state.sequence,
            weekly_hours=state.weekly_hours,
            plan_revision=state.plan_revision,
            focus_competency_ids=list(state.focus_competency_ids),
            evidence_history=list(state.evidence_history[-12:]),
            next_review_at=future_reviews[0].isoformat() if future_reviews else None,
        )

    def _generate_build_activities(
        self,
        *,
        role: RoleDefinition,
        mastery: dict[str, int],
        weekly_hours: int,
        focus_competency_ids: list[str],
        learner_name: str,
        experience_summary: str,
        seed: str,
        generation: int,
    ) -> list[ActivityView]:
        ranked = self._rank_competencies(role, mastery, focus_competency_ids)
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
                mastery=mastery.get(competency.identifier, 0),
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
    def _provisional_mastery_delta(
        *,
        criteria_met: int,
        criteria_total: int,
        confidence: int,
        reflection: str,
    ) -> int:
        ratio = criteria_met / max(criteria_total, 1)
        reflection_bonus = 4 if len(reflection.strip()) >= 80 else 0
        return min(25, 5 + round(10 * ratio) + (confidence * 2) + reflection_bonus)

    @staticmethod
    def _rank_competencies(
        role: RoleDefinition,
        mastery: dict[str, int],
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
                -(100 - mastery.get(item.identifier, 0)) * item.weight,
                item.identifier,
            ),
        )

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

    @staticmethod
    def _role_view(role: RoleDefinition) -> RoleView:
        return RoleView(
            id=role.identifier,
            version=role.version,
            title=role.title,
            summary=role.summary,
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
        mastery: int,
        focused: bool,
    ) -> ActivityView:
        selector_seed = hashlib.sha256(
            f"{seed}|{competency.identifier}|{position}|{generation}".encode()
        ).hexdigest()
        template = competency.activities[int(selector_seed[:4], 16) % len(competency.activities)]
        fingerprint = selector_seed[:12]
        context = experience_summary or "current self-assessment and target role"
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
                f"Selected from role profile {role.version} because current provisional mastery "
                f"is {mastery}% and the competency weight is {competency.weight}.{focus_reason}"
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
                f"Reproduce or critique the earlier evidence for {learner_name} without relying "
                "on the original step-by-step notes, then identify what still requires support."
            ),
            deliverable=(
                "A concise reproduction or review note linked to the earlier deliverable, with "
                "any regression, misconception, or improvement recorded."
            ),
            acceptance_criteria=list(source.acceptance_criteria),
            estimated_minutes=max(30, source.estimated_minutes // 2),
            kind="review",
            rationale=(
                "Scheduled as a spaced retrieval review from the previous learner-attested "
                "evidence cycle; it is not an external competency certification."
            ),
            generation=generation,
            available_from=available_from.isoformat(),
        )
