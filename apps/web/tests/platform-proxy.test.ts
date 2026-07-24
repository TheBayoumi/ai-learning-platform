import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "../app/api/platform/[...path]/route";

const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("platform API proxy", () => {
  it("forwards the allowlisted role catalog without exposing configuration", async () => {
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
  });

  it("forwards bounded JSON bodies and preserves upstream API errors", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json(
        { detail: { code: "INVALID_COMPETENCY_RATING", message: "Invalid ratings." } },
        { status: 400 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new Request("http://web.test/api/platform/plans", {
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
  });

  it("allows the adaptive replan route as a POST-only boundary", async () => {
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
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      }),
      context(["plans", "replan"])
    );

    expect(response.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      "http://127.0.0.1:8000/api/v1/plans/replan"
    );
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(JSON.stringify(body));
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
