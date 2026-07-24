"""Expiring assessment attempts with server-side answers and bounded feedback."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, ValidationError

from ai_learning_platform_api.learning.assessment_catalog import (
    ASSESSMENT_BANK_VERSION,
    QUESTION_BY_ID,
    QUESTIONS_BY_COMPETENCY,
)
from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.schemas import (
    AssessmentAttemptView,
    AssessmentFeedbackView,
    AssessmentOptionView,
    AssessmentQuestionView,
    AssessmentRecordView,
    AssessmentSubmitRequest,
    LearnerState,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]
_ATTEMPT_TTL = timedelta(minutes=30)


class AssessmentError(ValueError):
    """Base class for safe assessment-domain failures."""

    code = "ASSESSMENT_ERROR"


class InvalidAssessmentAttemptError(AssessmentError):
    """The signed attempt is malformed, mismatched, or expired."""

    code = "INVALID_ASSESSMENT_ATTEMPT"


class InvalidAssessmentAnswerError(AssessmentError):
    """Answers are missing, duplicated, or reference invalid options."""

    code = "INVALID_ASSESSMENT_ANSWER"


class AssessmentAttemptPayload(BaseModel):
    """Private signed attempt identity; it contains no correct answers."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    attempt_id: str
    bank_version: str
    learner_id: str
    role_id: str
    state_sequence: int
    issued_at: str
    expires_at: str
    question_ids: list[str]


@dataclass(frozen=True, slots=True)
class AssessmentOutcome:
    """Validated scoring output used to update learner state."""

    record: AssessmentRecordView
    feedback: tuple[AssessmentFeedbackView, ...]
    competency_scores: dict[str, int]


class AssessmentAttemptCodec:
    """Canonical HMAC codec with a key separated from learner-state signing."""

    def __init__(self, secret: str) -> None:
        secret_bytes = secret.encode("utf-8")
        if len(secret_bytes) < 32:
            raise ValueError("assessment secret must contain at least 32 UTF-8 bytes")
        self._key = hmac.new(
            secret_bytes,
            b"ai-learning-platform:assessment-attempt:v1",
            hashlib.sha256,
        ).digest()

    def encode(self, payload: AssessmentAttemptPayload) -> str:
        raw = json.dumps(
            payload.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._key, raw, hashlib.sha256).digest()
        return f"{_urlsafe_encode(raw)}.{_urlsafe_encode(signature)}"

    def decode(self, token: str) -> AssessmentAttemptPayload:
        if len(token) > 16_384 or token.count(".") != 1:
            raise InvalidAssessmentAttemptError
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        raw = _urlsafe_decode(encoded_payload)
        signature = _urlsafe_decode(encoded_signature)
        expected = hmac.new(self._key, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidAssessmentAttemptError
        try:
            return AssessmentAttemptPayload.model_validate_json(raw)
        except ValidationError as error:
            raise InvalidAssessmentAttemptError from error


class AssessmentCalibrationEngine:
    """Issue and score bounded calibration attempts for current priorities."""

    def __init__(
        self,
        secret: str,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory | None = None,
    ) -> None:
        self._codec = AssessmentAttemptCodec(secret)
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)
        self._id_factory = id_factory if id_factory is not None else uuid4

    def start(
        self,
        *,
        state: LearnerState,
        role: RoleDefinition,
        competency_ids: Sequence[str],
    ) -> AssessmentAttemptView:
        """Issue public questions for an ordered set of competency priorities."""
        selected = [
            QUESTIONS_BY_COMPETENCY[competency_id]
            for competency_id in competency_ids
            if competency_id in QUESTIONS_BY_COMPETENCY
        ]
        if len(selected) < 2:
            raise InvalidAssessmentAttemptError
        now = self._now()
        expires_at = now + _ATTEMPT_TTL
        payload = AssessmentAttemptPayload(
            attempt_id=str(self._id_factory()),
            bank_version=ASSESSMENT_BANK_VERSION,
            learner_id=state.learner_id,
            role_id=role.identifier,
            state_sequence=state.sequence,
            issued_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            question_ids=[question.identifier for question in selected],
        )
        competency_names = {
            competency.identifier: competency.name for competency in role.competencies
        }
        return AssessmentAttemptView(
            attempt_token=self._codec.encode(payload),
            bank_version=ASSESSMENT_BANK_VERSION,
            issued_at=payload.issued_at,
            expires_at=payload.expires_at,
            questions=[
                AssessmentQuestionView(
                    id=question.identifier,
                    competency_id=question.competency_id,
                    competency_name=competency_names[question.competency_id],
                    prompt=question.prompt,
                    options=[
                        AssessmentOptionView(id=option.identifier, text=option.text)
                        for option in question.options
                    ],
                )
                for question in selected
            ],
        )

    def score(
        self,
        *,
        state: LearnerState,
        role: RoleDefinition,
        request: AssessmentSubmitRequest,
    ) -> AssessmentOutcome:
        """Validate the attempt and return answer-hidden scoring feedback."""
        payload = self._codec.decode(request.attempt_token)
        now = self._now()
        if (
            payload.bank_version != ASSESSMENT_BANK_VERSION
            or payload.learner_id != state.learner_id
            or payload.role_id != role.identifier
            or payload.state_sequence != state.sequence
            or _parse_timestamp(payload.expires_at) < now
        ):
            raise InvalidAssessmentAttemptError

        expected_ids = payload.question_ids
        answer_map: dict[str, str] = {}
        for answer in request.answers:
            if answer.question_id in answer_map:
                raise InvalidAssessmentAnswerError
            answer_map[answer.question_id] = answer.option_id
        if set(answer_map) != set(expected_ids) or len(answer_map) != len(expected_ids):
            raise InvalidAssessmentAnswerError

        competency_scores: dict[str, int] = {}
        feedback: list[AssessmentFeedbackView] = []
        correct_count = 0
        for question_id in expected_ids:
            question = QUESTION_BY_ID.get(question_id)
            if question is None:
                raise InvalidAssessmentAttemptError
            valid_option_ids = {option.identifier for option in question.options}
            selected_option = answer_map[question_id]
            if selected_option not in valid_option_ids:
                raise InvalidAssessmentAnswerError
            correct = hmac.compare_digest(selected_option, question.correct_option_id)
            if correct:
                correct_count += 1
            competency_scores[question.competency_id] = 100 if correct else 0
            feedback.append(
                AssessmentFeedbackView(
                    question_id=question.identifier,
                    competency_id=question.competency_id,
                    correct=correct,
                    explanation=question.explanation,
                )
            )

        total_count = len(expected_ids)
        score_percent = round((correct_count / total_count) * 100)
        record = AssessmentRecordView(
            attempt_id=payload.attempt_id,
            bank_version=payload.bank_version,
            submitted_at=now.isoformat(),
            score_percent=score_percent,
            correct_count=correct_count,
            total_count=total_count,
            competency_scores=competency_scores,
        )
        return AssessmentOutcome(
            record=record,
            feedback=tuple(feedback),
            competency_scores=competency_scores,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("assessment clock must return a timezone-aware datetime")
        return value.astimezone(UTC)


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise InvalidAssessmentAttemptError from error


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidAssessmentAttemptError from error
    if parsed.tzinfo is None:
        raise InvalidAssessmentAttemptError
    return parsed.astimezone(UTC)
