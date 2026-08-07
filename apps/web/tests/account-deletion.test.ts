import { describe, expect, it, vi } from "vitest";

import {
  clearLocalLearningState,
  deleteCurrentAnonymousAccount
} from "../lib/account-deletion";
import { LEARNING_SESSION_STORAGE_KEY } from "../lib/learning-session";

describe("anonymous account deletion client", () => {
  it("requires exact destructive confirmation before network access", async () => {
    const fetcher = vi.fn<typeof fetch>();

    await expect(deleteCurrentAnonymousAccount("delete", fetcher)).rejects.toThrow(
      'Type "DELETE" exactly to confirm.'
    );
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("sends one same-origin DELETE and validates the result", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({ deleted: true, scope: "current_anonymous_account" })
    );

    await expect(deleteCurrentAnonymousAccount("DELETE", fetcher)).resolves.toEqual({
      deleted: true,
      scope: "current_anonymous_account"
    });
    expect(fetcher).toHaveBeenCalledWith("/api/platform/account", {
      method: "DELETE",
      headers: {
        accept: "application/json",
        "content-type": "application/json"
      },
      body: JSON.stringify({ confirmation: "DELETE" }),
      cache: "no-store",
      credentials: "same-origin"
    });
  });

  it("surfaces safe server failures and rejects malformed success payloads", async () => {
    const unavailable = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json(
        {
          detail: {
            code: "PERSISTENCE_UNAVAILABLE",
            message: "Account data could not be deleted right now."
          }
        },
        { status: 503 }
      )
    );
    await expect(deleteCurrentAnonymousAccount("DELETE", unavailable)).rejects.toThrow(
      "Account data could not be deleted right now."
    );

    const malformed = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({ deleted: "yes", scope: "current_anonymous_account" })
    );
    await expect(deleteCurrentAnonymousAccount("DELETE", malformed)).rejects.toThrow(
      "invalid response"
    );
  });

  it("clears only the platform learning-state key after server success", () => {
    const storage = {
      removeItem: vi.fn()
    } as unknown as Storage;

    clearLocalLearningState(storage);

    expect(storage.removeItem).toHaveBeenCalledTimes(1);
    expect(storage.removeItem).toHaveBeenCalledWith(LEARNING_SESSION_STORAGE_KEY);
  });
});
