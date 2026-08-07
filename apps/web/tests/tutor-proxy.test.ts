import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/platform/[...path]/route";

const context = { params: Promise.resolve({ path: ["tutor", "stream"] }) };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("tutor stream proxy", () => {
  it("relays an allowlisted SSE stream with server-only account context", async () => {
    const upstreamBody =
      'event: meta\ndata: {"model":"fake/model","prompt_version":"v1","authoritative":false}\n\n' +
      'event: delta\ndata: {"text":"Next step"}\n\n' +
      'event: done\ndata: {"status":"complete"}\n\n';
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(upstreamBody, {
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const requestBody = {
      state_token: "signed-token-with-sufficient-length",
      message: "Help",
      move: "hint",
      history: []
    };
    const response = await POST(
      new Request("https://web.test/api/platform/tutor/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(requestBody)
      }),
      context
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("text/event-stream; charset=utf-8");
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("x-accel-buffering")).toBe("no");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(await response.text()).toBe(upstreamBody);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      "http://127.0.0.1:8000/api/v1/tutor/stream"
    );
    const options = fetchMock.mock.calls[0]?.[1];
    expect(options?.body).toBe(JSON.stringify(requestBody));
    const headers = new Headers(options?.headers);
    expect(headers.get("accept")).toBe("text/event-stream");
    expect(headers.get("x-platform-account-id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(headers.get("x-platform-command-id")).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("rejects a successful non-SSE tutor response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(Response.json({ text: "unsafe" }))
    );

    const response = await POST(
      new Request("http://web.test/api/platform/tutor/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          state_token: "signed-token-with-sufficient-length",
          message: "Help"
        })
      }),
      context
    );

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: {
        code: "PLATFORM_UPSTREAM_INVALID",
        message: "The tutor service returned an invalid stream."
      }
    });
  });

  it("preserves safe JSON preflight errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json(
          {
            detail: {
              code: "TUTOR_UNAVAILABLE",
              message: "The tutor is temporarily unavailable; your learning plan is safe."
            }
          },
          { status: 503 }
        )
      )
    );

    const response = await POST(
      new Request("http://web.test/api/platform/tutor/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          state_token: "signed-token-with-sufficient-length",
          message: "Help"
        })
      }),
      context
    );

    expect(response.status).toBe(503);
    expect((await response.json()).detail.code).toBe("TUTOR_UNAVAILABLE");
  });
});
