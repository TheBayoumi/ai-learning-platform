"""Deterministic diagnosis, personalized work generation, and signed progress state."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CompetencyView,
    LearnerState,
    PlanRequest,
    PlanView,
    PriorityCompetencyView,
    ProgressRequest,
    RoleView,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


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


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise InvalidStateTokenError from error


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
    """Create and advance deterministic learner plans without server persistence."""

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

        rating_map: dict[str, int] = {}
        known_ids = {competency.identifier for competency in role.competencies}
        for rating in request.ratings:
            if rating.competency_id not in known_ids or rating.competency_id in rating_map:
                raise InvalidRatingError
            rating_map[rating.competency_id] = rating.score

        mastery = {
            competency.identifier: rating_map.get(competency.identifier, 0) * 25
            for competency in role.competencies
        }
        seed = hashlib.sha256(
            "|".join(
                (
                    request.learner_name.casefold().strip(),
                    request.target_role,
                    request.experience_summary.casefold().strip(),
                )
            ).encode("utf-8")
        ).hexdigest()
        ranked = sorted(
            role.competencies,
            key=lambda item: (-(100 - mastery[item.identifier]) * item.weight, item.identifier),
        )
        activity_count = min(len(ranked), max(4, request.weekly_hours // 2))
        activities = [
            self._activity_view(
                role=role,
                competency=competency,
                seed=seed,
                position=position,
                learner_name=request.learner_name.strip(),
                experience_summary=request.experience_summary.strip(),
            )
            for position, competency in enumerate(ranked[:activity_count], start=1)
        ]
        state = LearnerState(
            learner_id=str(self._id_factory()),
            learner_name=request.learner_name.strip(),
            target_role=request.target_role,
            weekly_hours=request.weekly_hours,
            experience_summary=request.experience_summary.strip(),
            created_at=self._clock().isoformat(),
            sequence=0,
            mastery=mastery,
            completed_activity_ids=[],
            activities=activities,
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
        """Accept one activity and issue the next tamper-evident learner state."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        activity = next((item for item in state.activities if item.id == request.activity_id), None)
        if activity is None:
            raise UnknownActivityError
        if activity.id in state.completed_activity_ids:
            raise ActivityAlreadyCompletedError

        completed = [*state.completed_activity_ids, activity.id]
        increment = 20 if len(request.reflection.strip()) >= 40 else 15
        mastery = dict(state.mastery)
        mastery[activity.competency_id] = min(
            100,
            mastery.get(activity.competency_id, 0) + increment,
        )
        updated = state.model_copy(
            update={
                "sequence": state.sequence + 1,
                "mastery": mastery,
                "completed_activity_ids": completed,
            }
        )
        return self._project(updated, role)

    def _project(self, state: LearnerState, role: RoleDefinition) -> PlanView:
        completed = set(state.completed_activity_ids)
        current = next((item for item in state.activities if item.id not in completed), None)
        priorities = sorted(
            role.competencies,
            key=lambda item: (-(100 - state.mastery.get(item.identifier, 0)) * item.weight, item.identifier),
        )[:4]
        total_weight = sum(item.weight for item in role.competencies)
        weighted_mastery = sum(
            state.mastery.get(item.identifier, 0) * item.weight for item in role.competencies
        )
        readiness = round(weighted_mastery / total_weight)
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
                )
                for item in priorities
            ],
            current_activity=current,
            completed_count=len(completed),
            total_count=len(state.activities),
            sequence=state.sequence,
        )

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
        competency: object,
        seed: str,
        position: int,
        learner_name: str,
        experience_summary: str,
    ) -> ActivityView:
        from ai_learning_platform_api.learning.catalog import CompetencyDefinition

        if not isinstance(competency, CompetencyDefinition):
            raise TypeError("competency must be a CompetencyDefinition")
        selector = int(seed[(position - 1) * 2 : position * 2], 16)
        template = competency.activities[selector % len(competency.activities)]
        fingerprint = hashlib.sha256(
            f"{seed}|{role.version}|{competency.identifier}|{position}".encode("utf-8")
        ).hexdigest()[:12]
        context = experience_summary or "current self-assessment and target role"
        return ActivityView(
            id=f"activity-{competency.identifier}-{fingerprint}",
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
        )
