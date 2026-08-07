import { readPlatformError } from "./learning-contract";
import { LEARNING_SESSION_STORAGE_KEY } from "./learning-session";

interface AccountDeletionView {
  readonly deleted: boolean;
  readonly scope: "current_anonymous_account";
}

function isAccountDeletionView(value: unknown): value is AccountDeletionView {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.deleted === "boolean" &&
    record.scope === "current_anonymous_account"
  );
}

export async function deleteCurrentAnonymousAccount(
  confirmation: string,
  fetcher: typeof fetch = fetch
): Promise<AccountDeletionView> {
  if (confirmation !== "DELETE") {
    throw new Error('Type "DELETE" exactly to confirm.');
  }
  const response = await fetcher("/api/platform/account", {
    method: "DELETE",
    headers: {
      accept: "application/json",
      "content-type": "application/json"
    },
    body: JSON.stringify({ confirmation }),
    cache: "no-store",
    credentials: "same-origin"
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The deletion service returned an unreadable response.");
  }
  if (!response.ok) {
    throw new Error(readPlatformError(payload));
  }
  if (!isAccountDeletionView(payload)) {
    throw new Error("The deletion service returned an invalid response.");
  }
  return payload;
}

export function clearLocalLearningState(storage: Storage): void {
  storage.removeItem(LEARNING_SESSION_STORAGE_KEY);
}
