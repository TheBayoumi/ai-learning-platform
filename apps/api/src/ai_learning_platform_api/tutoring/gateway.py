"""Provider-neutral streaming gateway with a Vercel AI Gateway adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

_MAX_DELTA_CHARACTERS = 2_048
_MAX_TOTAL_CHARACTERS = 12_000


class TutorGatewayError(RuntimeError):
    """A safe provider failure that must not affect learning state."""


@dataclass(frozen=True, slots=True)
class TutorGatewayMessage:
    """One provider-neutral conversation message."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class TutorGatewayRequest:
    """Versioned instructions and bounded messages sent to a model gateway."""

    instructions: str
    messages: tuple[TutorGatewayMessage, ...]


class TutorGateway(Protocol):
    """Replaceable model streaming boundary."""

    @property
    def available(self) -> bool: ...

    @property
    def model(self) -> str: ...

    def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]: ...

    async def aclose(self) -> None: ...


class DisabledTutorGateway:
    """Explicit safe degradation when no provider credential is available."""

    @property
    def available(self) -> bool:
        return False

    @property
    def model(self) -> str:
        return "unavailable"

    async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
        del request
        raise TutorGatewayError("tutor gateway is unavailable")
        yield ""  # pragma: no cover - preserves the async-iterator contract

    async def aclose(self) -> None:
        return None


class VercelAiGateway:
    """Stream normalized text deltas from the OpenAI-compatible Responses API."""

    def __init__(
        self,
        *,
        token: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "career-atlas-tutor/1",
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://ai-gateway.vercel.sh/v1",
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=min(5.0, timeout_seconds),
                pool=min(5.0, timeout_seconds),
            ),
            follow_redirects=False,
        )

    @property
    def available(self) -> bool:
        return True

    @property
    def model(self) -> str:
        return self._model

    async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "instructions": request.instructions,
            "input": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "max_output_tokens": self._max_output_tokens,
            "temperature": 0.2,
            "stream": True,
        }
        total_characters = 0
        try:
            async with self._client.stream(
                "POST",
                "/responses",
                headers=self._headers,
                json=payload,
            ) as response:
                if response.status_code != httpx.codes.OK:
                    await response.aread()
                    raise TutorGatewayError("tutor provider rejected the request")
                content_type = response.headers.get("content-type", "").lower()
                if not content_type.startswith("text/event-stream"):
                    raise TutorGatewayError("tutor provider returned an invalid stream")

                async for line in response.aiter_lines():
                    delta = _read_text_delta(line)
                    if delta is None:
                        continue
                    total_characters += len(delta)
                    if total_characters > _MAX_TOTAL_CHARACTERS:
                        raise TutorGatewayError("tutor provider exceeded the response limit")
                    yield delta
        except TutorGatewayError:
            raise
        except (httpx.HTTPError, TimeoutError) as error:
            raise TutorGatewayError("tutor provider is temporarily unavailable") from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _read_text_delta(line: str) -> str | None:
    if not line.startswith("data:"):
        return None
    raw = line.removeprefix("data:").strip()
    if not raw or raw == "[DONE]":
        return None
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as error:
        raise TutorGatewayError("tutor provider emitted invalid JSON") from error
    if not isinstance(event, dict) or event.get("type") != "response.output_text.delta":
        return None
    delta = event.get("delta")
    if not isinstance(delta, str) or not delta:
        return None
    if len(delta) > _MAX_DELTA_CHARACTERS:
        raise TutorGatewayError("tutor provider emitted an oversized delta")
    return delta
