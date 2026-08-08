from __future__ import annotations

import base64

import pytest

from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.learning.service import (
    InvalidStateTokenError,
    LearningPlanService,
    SignedStateCodec,
)

SECRET = "signed-state-security-secret-with-at-least-thirty-two-bytes"
_BASE64URL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _canonical_token() -> tuple[SignedStateCodec, str]:
    service = LearningPlanService(SECRET)
    created = service.create_plan(PlanRequest(learner_name="Canonical Token Learner"))
    return SignedStateCodec(SECRET), created.state_token


def _same_bytes_noncanonical_tail(value: str) -> str:
    """Change only unused Base64 padding bits while preserving decoded bytes."""
    index = _BASE64URL_ALPHABET.index(value[-1])
    alternative_index = (index & 0b111100) | ((index + 1) & 0b11)
    assert alternative_index != index
    alternative = f"{value[:-1]}{_BASE64URL_ALPHABET[alternative_index]}"

    padding = "=" * (-len(value) % 4)
    alternative_padding = "=" * (-len(alternative) % 4)
    assert base64.urlsafe_b64decode(value + padding) == base64.urlsafe_b64decode(
        alternative + alternative_padding
    )
    return alternative


def test_signed_state_rejects_byte_equivalent_noncanonical_signature() -> None:
    codec, token = _canonical_token()
    payload, signature = token.split(".", maxsplit=1)
    mutated_signature = _same_bytes_noncanonical_tail(signature)
    mutated = f"{payload}.{mutated_signature}"

    assert mutated != token
    with pytest.raises(InvalidStateTokenError):
        codec.decode(mutated)


def test_signed_state_rejects_explicit_padding_even_when_bytes_are_identical() -> None:
    codec, token = _canonical_token()
    payload, signature = token.split(".", maxsplit=1)
    padded_signature = f"{signature}{'=' * (-len(signature) % 4)}"
    assert padded_signature != signature

    with pytest.raises(InvalidStateTokenError):
        codec.decode(f"{payload}.{padded_signature}")


def test_signed_state_canonical_round_trip_still_succeeds() -> None:
    codec, token = _canonical_token()

    state = codec.decode(token)

    assert codec.encode(state) == token
