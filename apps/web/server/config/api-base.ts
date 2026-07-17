import "server-only";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
export const API_BASE_ENV_NAME = "AI_PLATFORM_API_BASE_URL";

declare const apiBaseUrlBrand: unique symbol;

export type ApiBaseUrl = string & {
  readonly [apiBaseUrlBrand]: "ApiBaseUrl";
};

export class ApiBaseConfigurationError extends Error {
  readonly code = "INVALID_API_BASE_URL";

  constructor() {
    super(
      "AI_PLATFORM_API_BASE_URL must be a canonical HTTP origin with an explicit port and the literal loopback host 127.0.0.1 or [::1]."
    );
    this.name = "ApiBaseConfigurationError";
  }
}

export function parseApiBaseUrl(
  configuredValue: string | undefined
): ApiBaseUrl {
  const candidate = configuredValue ?? DEFAULT_API_BASE_URL;
  if (candidate.length === 0 || candidate.trim() !== candidate) {
    throw new ApiBaseConfigurationError();
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new ApiBaseConfigurationError();
  }

  if (
    parsed.protocol !== "http:" ||
    (parsed.hostname !== "127.0.0.1" && parsed.hostname !== "[::1]") ||
    parsed.port === "" ||
    Number(parsed.port) < 1 ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    parsed.pathname !== "/" ||
    parsed.search !== "" ||
    parsed.hash !== "" ||
    (candidate !== parsed.origin && candidate !== `${parsed.origin}/`)
  ) {
    throw new ApiBaseConfigurationError();
  }

  return parsed.origin as ApiBaseUrl;
}

export function readApiBaseUrl(): ApiBaseUrl {
  return parseApiBaseUrl(process.env[API_BASE_ENV_NAME]);
}
