import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "../app/api/platform/[...path]/route";

const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

function forwardedHeaders(fetchMock: ReturnType<typeof vi.fn<typeof fetch>>): Headers {
  return new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("platform API proxy", () => {
  it("forwards the allowlisted role catalog without account context", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response('[{"id":"junior-python-backend-engineer"}]', {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(
      new Request("http://web.test/api/platform/roles"),
      context(["roles"])
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([
      { id: "junior-python-backend-engineer" }
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      "http://127.0.0.1:8000/api/v1/roles"
    );
    expect(forwardedHeaders(fetchMock).has("x-platform-account-id")).toBe(false);
  });

  it("creates a hardened anonymous account cookie for the first command", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json(
        { detail: { code: "INVALID_COMPETENCY_RATING", message: "Invalid ratings." } },
        { status: 400 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new Request("https://web.test/api/platform/plans", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ learner_name: "Mahmoud" })
      }),
      context(["plans"])
    );

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: { code: "INVALID_COMPETENCY_RATING", message: "Invalid ratings." }
    });
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({ learner_name: "Mahmoud" })
    );

    const headers = forwardedHeaders(fetchMock);
    expect(headers.get("x-platform-account-id")).toMatch(
      /^[0-9a-f-]{36}$/
    );
    expect(headers.get("x-platform-command-id")).toMatch(
      /^[0-9a-f-]{36}$/
    );
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(response.headers.get("set-cookie")).toContain("SameSite=Lax");
    expect(response.headers.get("set-cookie")).toContain("Secure");
  });

  it("reuses a valid account cookie without resetting it", async () => {
    const accountId = "11111111-1111-4111-8111-111111111111";
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({ plan_revision: 2 }, { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);
    const body = {
      state_token: "signed-token-with-sufficient-length",
      weekly_hours: 6,
      focus_competency_ids: ["fastapi"]
    };

    const response = await POST(
      new Request("http://web.test/api/platform/plans/replan", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          cookie: `other=value; ai_platform_account=${accountId}`
        },
        body: JSON.stringify(body)
      }),
      context(["plans", "replan"])
    );

    expect(response.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      "http://127.0.0.1:8000/api/v1/plans/replan"
    );
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(JSON.stringify(body));
    expect(forwardedHeaders(fetchMock).get("x-platform-account-id")).toBe(
      accountId
    );
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("replaces a malformed account cookie instead of forwarding it", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({ learner_id: "new" }, { status: 201 })
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new Request("http://web.test/api/platform/plans", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          cookie: "ai_platform_account=attacker-controlled"
        },
        body: JSON.stringify({ learner_name: "Mahmoud", ratings: [] })
      }),
      context(["plans"])
    );

    expect(response.status).toBe(201);
    expect(forwardedHeaders(fetchMock).get("x-platform-account-id")).not.toBe(
      "attacker-controlled"
    );
    expect(response.headers.get("set-cookie")).toContain("ai_platform_account=");
    expect(response.headers.get("set-cookie")).not.toContain("Secure");
  });

  it("rejects unknown paths before contacting the backend", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(
      new Request("http://web.test/api/platform/admin"),
      context(["admin"])
    );

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
