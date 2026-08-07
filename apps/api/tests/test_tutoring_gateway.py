from __future__ import annotations

import json

import httpx
import pytest

from ai_learning_platform_api.tutoring.gateway import (
    DisabledTutorGateway,
    TutorGatewayError,
    TutorGatewayMessage,
    TutorGatewayRequest,
    VercelAiGateway,
    _read_text_delta,
)

REQUEST = TutorGatewayRequest(
    instructions="bounded instructions",
    messages=(TutorGatewayMessage(role="user", content="help"),),
)


async def collect(gateway: VercelAiGateway) -> list[str]:
    return [delta async for delta in gateway.stream(REQUEST)]


def stream_response(*events: dict[str, object] | str) -> httpx.Response:
    body = "".join(
        f"data: {event if isinstance(event, str) else json.dumps(event)}\n\n"
        for event in events
    )
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream; charset=utf-8"},
        content=body,
    )


@pytest.mark.asyncio
async def test_vercel_gateway_streams_only_normalized_text_deltas() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://ai-gateway.vercel.sh/v1/responses"
        assert request.headers["authorization"] == "Bearer secret-token"
        payload = json.loads(request.content)
        assert payload["model"] == "alibaba/qwen3.5-flash"
        assert payload["max_output_tokens"] == 600
        assert payload["temperature"] == 0.2
        assert payload["stream"] is True
        assert payload["instructions"] == "bounded instructions"
        return stream_response(
            {"type": "response.created"},
            {"type": "response.output_text.delta", "delta": "First"},
            {"type": "response.output_text.delta", "delta": " step"},
            "[DONE]",
        )

    client = httpx.AsyncClient(
        base_url="https://ai-gateway.vercel.sh/v1",
        transport=httpx.MockTransport(handler),
    )
    gateway = VercelAiGateway(
        token="secret-token",
        model="alibaba/qwen3.5-flash",
        timeout_seconds=25,
        max_output_tokens=600,
        client=client,
    )
    assert gateway.available is True
    assert gateway.model == "alibaba/qwen3.5-flash"
    assert await collect(gateway) == ["First", " step"]
    await gateway.aclose()
    assert not client.is_closed
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(429, json={"error": "rate"}), "rejected"),
        (httpx.Response(200, json={"text": "not a stream"}), "invalid stream"),
        (stream_response("not-json"), "invalid JSON"),
        (
            stream_response(
                {"type": "response.output_text.delta", "delta": "x" * 2_049}
            ),
            "oversized delta",
        ),
    ],
)
async def test_vercel_gateway_fails_closed_on_invalid_provider_responses(
    response: httpx.Response,
    message: str,
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return response

    client = httpx.AsyncClient(
        base_url="https://ai-gateway.vercel.sh/v1",
        transport=httpx.MockTransport(handler),
    )
    gateway = VercelAiGateway(
        token="token",
        model="alibaba/qwen3.5-flash",
        timeout_seconds=5,
        max_output_tokens=128,
        client=client,
    )
    with pytest.raises(TutorGatewayError, match=message):
        await collect(gateway)
    await client.aclose()


@pytest.mark.asyncio
async def test_vercel_gateway_bounds_total_output() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return stream_response(
            *[
                {"type": "response.output_text.delta", "delta": "x" * 2_000}
                for _ in range(7)
            ]
        )

    client = httpx.AsyncClient(
        base_url="https://ai-gateway.vercel.sh/v1",
        transport=httpx.MockTransport(handler),
    )
    gateway = VercelAiGateway(
        token="token",
        model="model/id",
        timeout_seconds=5,
        max_output_tokens=128,
        client=client,
    )
    with pytest.raises(TutorGatewayError, match="response limit"):
        await collect(gateway)
    await client.aclose()


@pytest.mark.asyncio
async def test_vercel_gateway_sanitizes_transport_failures() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("credential=should-not-propagate", request=request)

    client = httpx.AsyncClient(
        base_url="https://ai-gateway.vercel.sh/v1",
        transport=httpx.MockTransport(handler),
    )
    gateway = VercelAiGateway(
        token="token",
        model="model/id",
        timeout_seconds=5,
        max_output_tokens=128,
        client=client,
    )
    with pytest.raises(TutorGatewayError, match="temporarily unavailable") as captured:
        await collect(gateway)
    assert "credential" not in str(captured.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_disabled_gateway_degrades_without_network() -> None:
    gateway = DisabledTutorGateway()
    assert gateway.available is False
    assert gateway.model == "unavailable"
    with pytest.raises(TutorGatewayError, match="unavailable"):
        _ = [delta async for delta in gateway.stream(REQUEST)]
    await gateway.aclose()


def test_read_text_delta_ignores_non_data_and_non_delta_events() -> None:
    assert _read_text_delta("event: response.created") is None
    assert _read_text_delta("data: ") is None
    assert _read_text_delta("data: [DONE]") is None
    assert _read_text_delta('data: {"type":"response.completed"}') is None
    assert _read_text_delta('data: {"type":"response.output_text.delta","delta":""}') is None
