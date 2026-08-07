"""Bounded per-instance tutor admission controls.

These controls are defense in depth for each serverless process. Production must still
configure provider spend limits and edge/WAF rate limits because instances do not share memory.
"""

from __future__ import annotations

import asyncio
import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic


class TutorAdmissionError(RuntimeError):
    """Base class for safe tutor admission failures."""

    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__()
        self.retry_after_seconds = retry_after_seconds


class TutorRateLimitError(TutorAdmissionError):
    """The account exceeded its fixed-window turn allowance."""


class TutorCapacityError(TutorAdmissionError):
    """The process reached its configured concurrent stream ceiling."""


@dataclass(slots=True)
class TutorTurnLease:
    """One admitted turn that releases capacity exactly once."""

    _limiter: TutorTurnLimiter
    _released: bool = field(default=False, init=False)

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        await self._limiter._release()


class TutorTurnLimiter:
    """Apply bounded fixed-window and concurrent-turn admission per process."""

    def __init__(
        self,
        *,
        max_concurrent_turns: int,
        requests_per_window: int,
        window_seconds: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._max_concurrent_turns = max_concurrent_turns
        self._requests_per_window = requests_per_window
        self._window_seconds = window_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._active_turns = 0
        self._requests: dict[str, deque[float]] = {}

    async def acquire(self, account_id: str) -> TutorTurnLease:
        now = self._clock()
        async with self._lock:
            self._prune(now)
            if self._active_turns >= self._max_concurrent_turns:
                raise TutorCapacityError(retry_after_seconds=1)

            requests = self._requests.setdefault(account_id, deque())
            threshold = now - self._window_seconds
            while requests and requests[0] <= threshold:
                requests.popleft()
            if len(requests) >= self._requests_per_window:
                retry_after = max(1, math.ceil(self._window_seconds - (now - requests[0])))
                raise TutorRateLimitError(retry_after_seconds=retry_after)

            requests.append(now)
            self._active_turns += 1
            return TutorTurnLease(self)

    async def _release(self) -> None:
        async with self._lock:
            self._active_turns = max(0, self._active_turns - 1)

    def _prune(self, now: float) -> None:
        threshold = now - self._window_seconds
        expired_accounts: list[str] = []
        for account_id, requests in self._requests.items():
            while requests and requests[0] <= threshold:
                requests.popleft()
            if not requests:
                expired_accounts.append(account_id)
        for account_id in expired_accounts:
            del self._requests[account_id]
