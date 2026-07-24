export const LEARNING_SESSION_STORAGE_KEY = "ai-career-learning-plan-v1";
export const LEARNING_ACCOUNT_STORAGE_KEY = "ai-career-anonymous-account-v1";

export type LearningSession =
  | Readonly<{
      mode: "signed_state";
      stateToken: string;
    }>
  | Readonly<{
      mode: "postgres";
      learnerId: string;
      version: number;
    }>;

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function readLearningSession(): LearningSession | null {
  const raw = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  if (!raw.startsWith("{")) {
    return raw.length >= 20 ? { mode: "signed_state", stateToken: raw } : null;
  }
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return null;
    }
    const record = value as Record<string, unknown>;
    if (record.mode === "signed_state" && typeof record.stateToken === "string") {
      return record.stateToken.length >= 20
        ? { mode: "signed_state", stateToken: record.stateToken }
        : null;
    }
    if (
      record.mode === "postgres" &&
      typeof record.learnerId === "string" &&
      UUID_V4_PATTERN.test(record.learnerId) &&
      typeof record.version === "number" &&
      Number.isInteger(record.version) &&
      record.version >= 0
    ) {
      return {
        mode: "postgres",
        learnerId: record.learnerId.toLowerCase(),
        version: record.version
      };
    }
  } catch {
    return null;
  }
  return null;
}

export function writeLearningSession(session: LearningSession): void {
  window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearLearningSession(): void {
  window.localStorage.removeItem(LEARNING_SESSION_STORAGE_KEY);
}

export function getOrCreateAnonymousAccountId(): string {
  const existing = window.localStorage.getItem(LEARNING_ACCOUNT_STORAGE_KEY);
  if (existing !== null && UUID_V4_PATTERN.test(existing)) {
    return existing.toLowerCase();
  }
  const created = window.crypto.randomUUID().toLowerCase();
  window.localStorage.setItem(LEARNING_ACCOUNT_STORAGE_KEY, created);
  return created;
}

export function createIdempotencyKey(action: string): string {
  return `${action}:${window.crypto.randomUUID()}`;
}
