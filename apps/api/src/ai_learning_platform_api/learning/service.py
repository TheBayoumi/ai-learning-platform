"""Deterministic adaptive planning and learner-attested evidence history."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import zlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_learning_platform_api.learning.assessment import AssessmentCalibrationEngine
from ai_learning_platform_api.learning.catalog import ROLE_CATALOG, RoleDefinition
from ai_learning_platform_api.learning.evidence import apply_trusted_verdict
from ai_learning_platform_api.learning.planner import (
    CurriculumDecision,
    diagnostic_signal_values,
    eligible_build_decisions,
    plan_version_id,
    rank_curriculum,
    target_fingerprint,
)
from ai_learning_platform_api.learning.role_profile import profile_for
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    AssessmentAttemptView,
    AssessmentStartRequest,
    AssessmentSubmissionView,
    AssessmentSubmitRequest,
    CompetencyEvidenceState,
    CompetencyView,
    CurriculumTrigger,
    EvidenceRecordView,
    LearnerPlanVersion,
    LearnerState,
    PlanDeltaView,
    PlanPrioritySnapshot,
    PlanRequest,
    PlanView,
    PriorityCompetencyView,
    ProgressRequest,
    ReplanRequest,
    RoleView,
    TargetView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.targeting import default_target_for, resolve_target

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]

_MAX_EVIDENCE_HISTORY = 24
_MAX_ASSESSMENT_HISTORY = 12
_MAX_COMPLETED_IDS = 128
_MAX_PLAN_VERSIONS = 3
_REVIEW_INTERVAL_DAYS = {0: 1, 1: 2, 2: 4, 3: 7, 4: 14}
_MAX_STATE_PAYLOAD_BYTES = 262_144
_STATE_COMPRESSION_PREFIX = b"Z1"


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


def _decode_state_payload(packed: bytes) -> bytes:
    """Decode compressed state with an explicit output bound; raw JSON is legacy-only."""
    if packed.startswith(_STATE_COMPRESSION_PREFIX):
        decompressor = zlib.decompressobj()
        try:
            payload = decompressor.decompress(
                packed[len(_STATE_COMPRESSION_PREFIX) :],
                _MAX_STATE_PAYLOAD_BYTES + 1,
            )
        except zlib.error as error:
            raise InvalidStateTokenError from error
        if (
            len(payload) > _MAX_STATE_PAYLOAD_BYTES
            or not decompressor.eof
            or decompressor.unused_data
            or decompressor.unconsumed_tail
        ):
            raise InvalidStateTokenError
        return payload
    if len(packed) > _MAX_STATE_PAYLOAD_BYTES or not packed.startswith(b"{"):
        raise InvalidStateTokenError
    return packed


class SignedStateCodec:
    """Canonical HMAC codec for bounded compressed browser-carried learner state."""

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
        if len(payload) > _MAX_STATE_PAYLOAD_BYTES:
            raise InvalidStateTokenError
        packed = _STATE_COMPRESSION_PREFIX + zlib.compress(payload, level=9)
        signature = hmac.new(self._secret, packed, hashlib.sha256).digest()
        token = f"{_urlsafe_encode(packed)}.{_urlsafe_encode(signature)}"
        if len(token) > 65_536:
            raise InvalidStateTokenError
        return token

    def decode(self, token: str) -> LearnerState:
        if len(token) > 65_536 or token.count(".") != 1:
            raise InvalidStateTokenError
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        packed = _urlsafe_decode(encoded_payload)
        signature = _urlsafe_decode(encoded_signature)
        expected = hmac.new(self._secret, packed, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidStateTokenError
        payload = _decode_state_payload(packed)
        try:
            decoded = json.loads(payload)
            return LearnerState.model_validate(decoded)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
            raise InvalidStateTokenError from error


class LearningPlanService:
    """Create, advance, and replan deterministic learner-specific curricula."""

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
        """Return versioned role candidates with exact graph and evidence-policy metadata."""
        return [self._role_view(role) for role in ROLE_CATALOG.values()]

    def create_plan(self, request: PlanRequest) -> PlanView:
        """Resolve Target and create the first immutable learner-specific plan version."""
        role = ROLE_CATALOG.get(request.target_role)
        if role is None:
            raise UnknownRoleError

        target = resolve_target(role, request.target)
        rating_map = self._rating_map(role, request)
        planning_signal = {
            competency.identifier: rating_map.get(competency.identifier, 0) * 25
            for competency in role.competencies
        }
        competency_evidence = {
            item.identifier: CompetencyEvidenceState(competency_id=item.identifier)
            for item in role.competencies
        }
        decisions = rank_curriculum(
            role=role,
            planning_signal=planning_signal,
            assessment_scores={},
            competency_evidence=competency_evidence,
            misconceptions=[],
            focus_competency_ids=[],
        )
        learner_id = str(self._id_factory())
        now = self._now()
        seed = self._learner_seed(
            request.learner_name,
            request.target_role,
            request.experience_summary,
        )
        activities = self._generate_build_activities(
            role=role,
            decisions=decisions,
            weekly_hours=request.weekly_hours,
            learner_name=request.learner_name.strip(),
            experience_summary=request.experience_summary.strip(),
            seed=seed,
            generation=0,
        )
        initial_version = self._plan_version(
            learner_id=learner_id,
            role=role,
            target=target,
            revision=0,
            created_at=now,
            trigger="initial",
            weekly_hours=request.weekly_hours,
            focus_competency_ids=[],
            decisions=decisions,
            activities=activities,
            previous=None,
        )
        state = LearnerState(
            schema_version=6,
            learner_id=learner_id,
            learner_name=request.learner_name.strip(),
            target_role=request.target_role,
            target=target,
            weekly_hours=request.weekly_hours,
            experience_summary=request.experience_summary.strip(),
            created_at=now.isoformat(),
            sequence=0,
            planning_signal=planning_signal,
            mastery={},
            completed_activity_ids=[],
            activities=activities,
            plan_revision=0,
            active_plan_version_id=initial_version.plan_version_id,
            plan_versions=[initial_version],
            focus_competency_ids=[],
            evidence_history=[],
            competency_evidence=competency_evidence,
        )
        return self._project(state, role)

    def resume(self, state_token: str) -> PlanView:
        """Verify, upgrade, and replay a previously issued learner state."""
        state = self._codec.decode(state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        return self._project(self._upgrade_state(state, role), role)

    def start_assessment(self, request: AssessmentStartRequest) -> AssessmentAttemptView:
        """Issue an expiring calibration attempt for current evidence-aware priorities."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        decisions = self._decisions(state, role)
        unresolved = [item for item in decisions if item.evidence_status != "independent"]
        diagnostic_priorities = sorted(
            unresolved,
            key=lambda item: (-item.score, item.competency.identifier),
        )
        priorities = diagnostic_priorities[: request.question_count]
        return self._assessment.start(
            state=state,
            role=role,
            competency_ids=[item.competency.identifier for item in priorities],
        )

    def submit_assessment(self, request: AssessmentSubmitRequest) -> AssessmentSubmissionView:
        """Score calibration and create a new immutable diagnostic-informed plan version."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        outcome = self._assessment.score(state=state, role=role, request=request)
        assessment_scores = dict(state.assessment_scores)
        assessment_scores.update(outcome.competency_scores)
        revision = state.plan_revision + 1
        decisions = rank_curriculum(
            role=role,
            planning_signal=state.planning_signal,
            assessment_scores=assessment_scores,
            competency_evidence=state.competency_evidence,
            misconceptions=state.misconceptions,
            focus_competency_ids=state.focus_competency_ids,
        )
        pending_reviews = self._pending_reviews(state)
        build_activities = self._generate_build_activities(
            role=role,
            decisions=decisions,
            weekly_hours=state.weekly_hours,
            learner_name=state.learner_name,
            experience_summary=state.experience_summary,
            seed=self._learner_seed(
                state.learner_name,
                state.target_role,
                f"{state.experience_summary}|assessment:{outcome.record.attempt_id}",
            ),
            generation=revision,
        )
        activities = [*pending_reviews, *build_activities]
        version = self._plan_version(
            learner_id=state.learner_id,
            role=role,
            target=self._required_target(state),
            revision=revision,
            created_at=self._now(),
            trigger="assessment",
            weekly_hours=state.weekly_hours,
            focus_competency_ids=state.focus_competency_ids,
            decisions=decisions,
            activities=activities,
            previous=self._active_plan_version(state),
        )
        updated = state.model_copy(
            update={
                "schema_version": 6,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "active_plan_version_id": version.plan_version_id,
                "plan_versions": self._append_plan_version(state, version),
                "assessment_scores": assessment_scores,
                "assessment_history": [*state.assessment_history, outcome.record][
                    -_MAX_ASSESSMENT_HISTORY:
                ],
                "activities": activities,
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
        """Record learner-attested work without promoting it to authoritative evidence."""
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
            source_item_family_id=activity.item_family_id,
            source_item_family_version=activity.item_family_version,
            source_blueprint_id=activity.blueprint_id,
            source_blueprint_version=activity.blueprint_version,
            source_rubric_version=activity.rubric_version,
            source_plan_version_id=activity.plan_version_id,
            source_semantic_fingerprint=activity.semantic_fingerprint,
            source_semantic_signature=activity.semantic_signature,
            source_high_stakes_eligible=activity.high_stakes_eligible,
        )
        review_activity = self._review_activity(
            source=activity,
            learner_name=state.learner_name,
            generation=state.sequence + 1,
            available_from=review_at,
        )
        updated = state.model_copy(
            update={
                "schema_version": 6,
                "sequence": state.sequence + 1,
                "planning_signal": planning_signal,
                "mastery": {},
                "completed_activity_ids": completed,
                "activities": [*state.activities, review_activity],
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
        """Apply a trusted verdict and deterministically replan from authoritative state."""
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

        revision = state.plan_revision + 1
        transitioned = transition.state
        decisions = rank_curriculum(
            role=role,
            planning_signal=transitioned.planning_signal,
            assessment_scores=transitioned.assessment_scores,
            competency_evidence=transitioned.competency_evidence,
            misconceptions=transitioned.misconceptions,
            focus_competency_ids=transitioned.focus_competency_ids,
        )
        activities = [
            *self._pending_reviews(transitioned),
            *self._generate_build_activities(
                role=role,
                decisions=decisions,
                weekly_hours=transitioned.weekly_hours,
                learner_name=transitioned.learner_name,
                experience_summary=transitioned.experience_summary,
                seed=self._learner_seed(
                    transitioned.learner_name,
                    transitioned.target_role,
                    f"{transitioned.experience_summary}|trusted:{verdict.evidence_id}:{revision}",
                ),
                generation=revision,
            ),
        ]
        version = self._plan_version(
            learner_id=transitioned.learner_id,
            role=role,
            target=self._required_target(transitioned),
            revision=revision,
            created_at=self._now(),
            trigger="trusted_evidence",
            weekly_hours=transitioned.weekly_hours,
            focus_competency_ids=transitioned.focus_competency_ids,
            decisions=decisions,
            activities=activities,
            previous=self._active_plan_version(state),
        )
        updated = transitioned.model_copy(
            update={
                "schema_version": 6,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "activities": activities,
                "active_plan_version_id": version.plan_version_id,
                "plan_versions": self._append_plan_version(state, version),
            }
        )
        return self._project(updated, role)

    def replan(self, request: ReplanRequest) -> PlanView:
        """Regenerate active work from evidence state, capacity, and explicit focus."""
        state = self._codec.decode(request.state_token)
        role = ROLE_CATALOG.get(state.target_role)
        if role is None:
            raise InvalidStateTokenError
        state = self._upgrade_state(state, role)
        focus = self._validated_focus(role, request.focus_competency_ids)
        revision = state.plan_revision + 1
        decisions = rank_curriculum(
            role=role,
            planning_signal=state.planning_signal,
            assessment_scores=state.assessment_scores,
            competency_evidence=state.competency_evidence,
            misconceptions=state.misconceptions,
            focus_competency_ids=focus,
        )
        seed = self._learner_seed(
            state.learner_name,
            state.target_role,
            f"{state.experience_summary}|revision:{revision}",
        )
        activities = [
            *self._pending_reviews(state),
            *self._generate_build_activities(
                role=role,
                decisions=decisions,
                weekly_hours=request.weekly_hours,
                learner_name=state.learner_name,
                experience_summary=state.experience_summary,
                seed=seed,
                generation=revision,
            ),
        ]
        version = self._plan_version(
            learner_id=state.learner_id,
            role=role,
            target=self._required_target(state),
            revision=revision,
            created_at=self._now(),
            trigger="manual_replan",
            weekly_hours=request.weekly_hours,
            focus_competency_ids=focus,
            decisions=decisions,
            activities=activities,
            previous=self._active_plan_version(state),
        )
        updated = state.model_copy(
            update={
                "schema_version": 6,
                "weekly_hours": request.weekly_hours,
                "sequence": state.sequence + 1,
                "plan_revision": revision,
                "active_plan_version_id": version.plan_version_id,
                "plan_versions": self._append_plan_version(state, version),
                "focus_competency_ids": focus,
                "activities": activities,
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
        diagnostic_signal = diagnostic_signal_values(
            role, state.planning_signal, state.assessment_scores
        )
        decisions = self._decisions(state, role)
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
        active_version = self._active_plan_version(state)
        if active_version is None:
            raise InvalidStateTokenError
        return PlanView(
            state_token=self._codec.encode(state),
            learner_id=state.learner_id,
            learner_name=state.learner_name,
            role=self._role_view(role),
            target=self._required_target(state),
            claim_state="validation_locked",
            verified_readiness_percent=None,
            planning_signal_percent=planning_signal_percent,
            diagnostic_signal_percent=diagnostic_signal_percent,
            assessment_coverage_percent=assessment_coverage,
            priority_competencies=[
                PriorityCompetencyView(
                    id=item.competency.identifier,
                    name=item.competency.name,
                    category=item.competency.category,
                    planning_signal_percent=state.planning_signal.get(
                        item.competency.identifier, 0
                    ),
                    diagnostic_signal_percent=item.diagnostic_signal_percent,
                    assessment_percent=state.assessment_scores.get(item.competency.identifier),
                    priority_gap_percent=100 - item.diagnostic_signal_percent,
                    authoritative_gap_percent=item.authoritative_gap_percent,
                    evidence_status=item.evidence_status,
                    prerequisite_ids=list(item.profile.prerequisites),
                    blocked_by=list(item.blocked_by),
                    active_misconception_codes=list(item.active_misconception_codes),
                    priority_reason=item.reason,
                    focused=item.focused,
                )
                for item in decisions
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
            completed_count=len(state.completed_activity_ids),
            total_count=len(state.activities),
            sequence=state.sequence,
            weekly_hours=state.weekly_hours,
            plan_revision=state.plan_revision,
            active_plan_version=active_version,
            plan_history=list(state.plan_versions),
            focus_competency_ids=list(state.focus_competency_ids),
            evidence_history=list(state.evidence_history[-12:]),
            assessment_history=list(state.assessment_history[-8:]),
            next_review_at=all_review_dates[0].isoformat() if all_review_dates else None,
        )

    def _decisions(
        self, state: LearnerState, role: RoleDefinition
    ) -> tuple[CurriculumDecision, ...]:
        return rank_curriculum(
            role=role,
            planning_signal=state.planning_signal,
            assessment_scores=state.assessment_scores,
            competency_evidence=state.competency_evidence,
            misconceptions=state.misconceptions,
            focus_competency_ids=state.focus_competency_ids,
        )

    def _generate_build_activities(
        self,
        *,
        role: RoleDefinition,
        decisions: tuple[CurriculumDecision, ...],
        weekly_hours: int,
        learner_name: str,
        experience_summary: str,
        seed: str,
        generation: int,
    ) -> list[ActivityView]:
        eligible = eligible_build_decisions(decisions)
        maximum_count = max(1, weekly_hours // 2)
        budget_minutes = weekly_hours * 60
        selected: list[ActivityView] = []
        used_minutes = 0
        for position, decision in enumerate(eligible, start=1):
            if len(selected) >= maximum_count:
                break
            activity = self._activity_view(
                role=role,
                decision=decision,
                seed=seed,
                position=position,
                learner_name=learner_name,
                experience_summary=experience_summary,
                generation=generation,
            )
            if selected and used_minutes + activity.estimated_minutes > budget_minutes:
                continue
            selected.append(activity)
            used_minutes += activity.estimated_minutes
            if used_minutes >= budget_minutes:
                break
        return selected

    @staticmethod
    def _pending_reviews(state: LearnerState) -> list[ActivityView]:
        return [
            activity
            for activity in state.activities
            if activity.kind == "review" and activity.id not in state.completed_activity_ids
        ]

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
        graph = profile_for(role)
        priorities = [item.snapshot(rank) for rank, item in enumerate(decisions, start=1)]
        target_hash = target_fingerprint(target)
        identifier = plan_version_id(
            learner_id=learner_id,
            role_version=role.version,
            revision=revision,
            target_hash=target_hash,
            trigger=trigger,
            activity_ids=[item.id for item in activities],
            priority_ids=[item.competency_id for item in priorities],
        )
        delta = self._plan_delta(previous, activities, priorities, trigger)
        return LearnerPlanVersion(
            plan_version_id=identifier,
            revision=revision,
            created_at=created_at.isoformat(),
            trigger=trigger,
            role_id=role.identifier,
            role_version=role.version,
            graph_version=graph.graph_version,
            evidence_policy_version=graph.evidence_policy_version,
            target_fingerprint=target_hash,
            weekly_hours=weekly_hours,
            focus_competency_ids=list(focus_competency_ids),
            priorities=priorities,
            activities=list(activities),
            delta=delta,
        )

    @staticmethod
    def _plan_delta(
        previous: LearnerPlanVersion | None,
        activities: list[ActivityView],
        priorities: list[PlanPrioritySnapshot],
        trigger: CurriculumTrigger,
    ) -> PlanDeltaView:
        current_ids = [item.id for item in activities]
        if previous is None:
            return PlanDeltaView(
                previous_plan_version_id=None,
                added_activity_ids=current_ids,
                removed_activity_ids=[],
                retained_activity_ids=[],
                priority_changes=[
                    f"{item.competency_id}:new-rank-{item.rank}" for item in priorities
                ],
                reason=f"{trigger}: initial deterministic curriculum snapshot",
            )
        previous_ids = [item.id for item in previous.activities]
        previous_set = set(previous_ids)
        current_set = set(current_ids)
        previous_ranks = {item.competency_id: item.rank for item in previous.priorities}
        priority_changes = [
            f"{item.competency_id}:{previous_ranks.get(item.competency_id, 'new')}->{item.rank}"
            for item in priorities
            if previous_ranks.get(item.competency_id) != item.rank
        ]
        return PlanDeltaView(
            previous_plan_version_id=previous.plan_version_id,
            added_activity_ids=[item for item in current_ids if item not in previous_set],
            removed_activity_ids=[item for item in previous_ids if item not in current_set],
            retained_activity_ids=[item for item in current_ids if item in previous_set],
            priority_changes=priority_changes,
            reason=(
                f"{trigger}: recalculated from exact target/profile, authoritative evidence, "
                "prerequisites, misconceptions, capacity, then diagnostic ordering signals"
            ),
        )

    @staticmethod
    def _append_plan_version(
        state: LearnerState, version: LearnerPlanVersion
    ) -> list[LearnerPlanVersion]:
        return [*state.plan_versions, version][-_MAX_PLAN_VERSIONS:]

    @staticmethod
    def _active_plan_version(state: LearnerState) -> LearnerPlanVersion | None:
        if state.active_plan_version_id is None:
            return None
        return next(
            (
                item
                for item in state.plan_versions
                if item.plan_version_id == state.active_plan_version_id
            ),
            None,
        )

    @staticmethod
    def _required_target(state: LearnerState) -> TargetView:
        if state.target is None:
            raise InvalidStateTokenError
        return state.target

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
        """Migrate legacy signed state into schema v6 without inventing trusted evidence."""
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
        plan_versions = list(state.plan_versions)
        active_plan_version_id = state.active_plan_version_id
        if not plan_versions:
            decisions = rank_curriculum(
                role=role,
                planning_signal=planning_signal,
                assessment_scores=state.assessment_scores,
                competency_evidence=competency_evidence,
                misconceptions=state.misconceptions,
                focus_competency_ids=state.focus_competency_ids,
            )
            graph = profile_for(role)
            target_hash = target_fingerprint(target)
            priorities = [item.snapshot(rank) for rank, item in enumerate(decisions, start=1)]
            identifier = plan_version_id(
                learner_id=state.learner_id,
                role_version=role.version,
                revision=state.plan_revision,
                target_hash=target_hash,
                trigger="state_migration",
                activity_ids=[item.id for item in state.activities],
                priority_ids=[item.competency_id for item in priorities],
            )
            migration = LearnerPlanVersion(
                plan_version_id=identifier,
                revision=state.plan_revision,
                created_at=state.created_at,
                trigger="state_migration",
                role_id=role.identifier,
                role_version=role.version,
                graph_version=graph.graph_version,
                evidence_policy_version=graph.evidence_policy_version,
                target_fingerprint=target_hash,
                weekly_hours=state.weekly_hours,
                focus_competency_ids=list(state.focus_competency_ids),
                priorities=priorities,
                activities=list(state.activities),
                delta=PlanDeltaView(
                    previous_plan_version_id=None,
                    added_activity_ids=[item.id for item in state.activities],
                    removed_activity_ids=[],
                    retained_activity_ids=[],
                    priority_changes=[
                        f"{item.competency_id}:migrated-rank-{item.rank}" for item in priorities
                    ],
                    reason=(
                        "state_migration: preserved legacy curriculum without inventing evidence"
                    ),
                ),
            )
            plan_versions = [migration]
            active_plan_version_id = migration.plan_version_id
        elif active_plan_version_id is None or not any(
            item.plan_version_id == active_plan_version_id for item in plan_versions
        ):
            raise InvalidStateTokenError
        return state.model_copy(
            update={
                "schema_version": 6,
                "target": target,
                "planning_signal": planning_signal,
                "mastery": {},
                "evidence_history": evidence_history,
                "competency_evidence": competency_evidence,
                "active_plan_version_id": active_plan_version_id,
                "plan_versions": plan_versions[-_MAX_PLAN_VERSIONS:],
            }
        )

    @staticmethod
    def _role_view(role: RoleDefinition) -> RoleView:
        graph = profile_for(role)
        return RoleView(
            id=role.identifier,
            version=role.version,
            title=role.title,
            summary=role.summary,
            graph_version=graph.graph_version,
            evidence_policy_version=graph.evidence_policy_version,
            validation_state="provisional",
            default_target=default_target_for(role),
            competencies=[
                CompetencyView(
                    id=item.identifier,
                    name=item.name,
                    category=item.category,
                    description=item.description,
                    weight=item.weight,
                    prerequisites=list(graph.competencies[item.identifier].prerequisites),
                    evidence_requirements=list(
                        graph.competencies[item.identifier].evidence_requirements
                    ),
                )
                for item in role.competencies
            ],
        )

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
        competency = decision.competency
        selector_seed = hashlib.sha256(
            f"{seed}|{competency.identifier}|{position}|{generation}".encode()
        ).hexdigest()
        template = competency.activities[int(selector_seed[:4], 16) % len(competency.activities)]
        fingerprint = selector_seed[:12]
        context = experience_summary or "current self-report and resolved target"
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
                f"Selected from provisional role profile {role.version}. {decision.reason}. "
                "The task is scheduled only because its prerequisites are authoritatively clear; "
                "completion itself is not verified mastery and will not grant mastery."
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
                "Completion remains a planning signal until independent retention evidence exists."
            ),
            generation=generation,
            available_from=available_from.isoformat(),
        )
