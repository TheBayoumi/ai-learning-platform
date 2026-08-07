from __future__ import annotations

import asyncio

import pytest

from ai_learning_platform_api.tutoring.limits import (
    TutorCapacityError,
    TutorRateLimitError,
    TutorTurnLimiter,
)

ACCOUNT_A = "11111111-1111-4111-8111-111111111111"
ACCOUNT_B = "22222222-2222-4222-8222-222222222222"


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_limiter_enforces_concurrency_and_idempotent_release() -> None:
    clock = FakeClock()
    limiter = TutorTurnLimiter(
        max_concurrent_turns=1,
        requests_per_window=10,
        window_seconds=60,
        clock=clock,
    )

    async def exercise() -> None:
        lease = await limiter.acquire(ACCOUNT_A)
        with pytest.raises(TutorCapacityError) as captured:
            await limiter.acquire(ACCOUNT_B)
        assert captured.value.retry_after_seconds == 1

        await lease.release()
        await lease.release()
        second = await limiter.acquire(ACCOUNT_B)
        await second.release()

    asyncio.run(exercise())


def test_limiter_applies_fixed_window_per_account() -> None:
    clock = FakeClock()
    limiter = TutorTurnLimiter(
        max_concurrent_turns=3,
        requests_per_window=2,
        window_seconds=60,
        clock=clock,
    )

    async def exercise() -> None:
        first = await limiter.acquire(ACCOUNT_A)
        await first.release()
        clock.now += 10
        second = await limiter.acquire(ACCOUNT_A)
        await second.release()

        with pytest.raises(TutorRateLimitError) as captured:
            await limiter.acquire(ACCOUNT_A)
        assert captured.value.retry_after_seconds == 50

        other = await limiter.acquire(ACCOUNT_B)
        await other.release()

        clock.now += 50
        next_window = await limiter.acquire(ACCOUNT_A)
        await next_window.release()

    asyncio.run(exercise())


def test_limiter_prunes_expired_account_buckets() -> None:
    clock = FakeClock()
    limiter = TutorTurnLimiter(
        max_concurrent_turns=1,
        requests_per_window=1,
        window_seconds=10,
        clock=clock,
    )

    async def exercise() -> None:
        lease = await limiter.acquire(ACCOUNT_A)
        await lease.release()
        assert ACCOUNT_A in limiter._requests
        clock.now += 11
        other = await limiter.acquire(ACCOUNT_B)
        assert ACCOUNT_A not in limiter._requests
        await other.release()

    asyncio.run(exercise())
