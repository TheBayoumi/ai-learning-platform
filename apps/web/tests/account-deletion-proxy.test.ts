import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE } from "../app/api/platform/[...path]/route";

const context = { params: Promise.resolve({ path: ["account"] }) };
const accountId = "11111111-1111-4111-8111-111111111111";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("anonymous account deletion proxy", () => {
  it("forwards only the HttpOnly-cookie identity and expires it after success", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({ deleted: true, scope: "current_anonymous_account" })
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await DELETE(
      new Request("https://web.test/api/platform/account", {
        method: "DELETE",
        headers: {
          cookie: `ai_platform_account=${accountId}`,
          "content-type": "application/json"
        },
        body: JSON.stringify({ confirmation: "DELETE" })
      }),
      context
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      deleted: true,
      scope: "current_anonymous_account"
    });
    expect(response.headers.get("set-cookie")).toContain("ai_platform_account=");
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(response.headers.get("set-cookie")).toContain("Secure");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const options = fetchMock.mock.calls[0]?.[1];
    const headers = new Headers(options?.headers);
    expect(headers.get("x-platform-account-id")).toBe(accountId);
    expect(headers.get("x-platform-command-id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(options?.body).toBe(JSON.stringify({ confirmation: "DELETE" }));
  });

  it("does not create an account when no valid cookie exists", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    const response = await DELETE(
      new Request("http://web.test/api/platform/account", {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ confirmation: "DELETE" })
      }),
      context
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      deleted: false,
      scope: "current_anonymous_account"
    });
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(response.headers.get("set-cookie")).not.toContain("Secure");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps the account cookie when upstream deletion fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json(
          {
            detail: {
              code: "PERSISTENCE_UNAVAILABLE",
              message: "Account data could not be deleted right now."
            }
          },
          { status: 503 }
        )
      )
    );

    const response = await DELETE(
      new Request("https://web.test/api/platform/account", {
        method: "DELETE",
        headers: {
          cookie: `ai_platform_account=${accountId}`,
          "content-type": "application/json"
        },
        body: JSON.stringify({ confirmation: "DELETE" })
      }),
      context
    );

    expect(response.status).toBe(503);
    expect(response.headers.get("set-cookie")).toBeNull();
    expect((await response.json()).detail.code).toBe("PERSISTENCE_UNAVAILABLE");
  });
});
