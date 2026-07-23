import "server-only";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
export const API_BASE_ENV_NAME = "AI_PLATFORM_API_BASE_URL";

declare const apiBaseUrlBrand: unique symbol;

export type ApiBaseUrl = string & {
  readonly [apiBaseUrlBrand]: "ApiBaseUrl";
};

interface ParseApiBaseOptions {
  readonly allowRemoteHttps?: boolean;
}

export class ApiBaseConfigurationError extends Error {
  readonly code = "INVALID_API_BASE_URL";

  constructor() {
    super(
      "AI_PLATFORM_API_BASE_URL must be a canonical loopback HTTP origin or, in a production server context, a canonical public HTTPS origin."
    );
    this.name = "ApiBaseConfigurationError";
  }
}

export function parseApiBaseUrl(
  configuredValue: string | undefined,
  options: ParseApiBaseOptions = {}
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

  const hasCleanOriginShape =
    parsed.username === "" &&
    parsed.password === "" &&
    parsed.pathname === "/" &&
    parsed.search === "" &&
    parsed.hash === "" &&
    (candidate === parsed.origin || candidate === `${parsed.origin}/`);
  if (!hasCleanOriginShape) {
    throw new ApiBaseConfigurationError();
  }

  const isLoopback =
    parsed.protocol === "http:" &&
    (parsed.hostname === "127.0.0.1" || parsed.hostname === "[::1]") &&
    parsed.port !== "" &&
    Number(parsed.port) >= 1 &&
    Number(parsed.port) <= 65_535;
  if (isLoopback) {
    return parsed.origin as ApiBaseUrl;
  }

  const hostname = parsed.hostname.toLowerCase();
  const isRemoteHttps =
    options.allowRemoteHttps === true &&
    parsed.protocol === "https:" &&
    parsed.port === "" &&
    hostname.includes(".") &&
    hostname !== "localhost" &&
    !hostname.endsWith(".localhost") &&
    !hostname.endsWith(".local") &&
    !/^\d+(?:\.\d+){3}$/u.test(hostname) &&
    !hostname.includes(":");
  if (!isRemoteHttps) {
    throw new ApiBaseConfigurationError();
  }

  return parsed.origin as ApiBaseUrl;
}

export function readApiBaseUrl(): ApiBaseUrl {
  return parseApiBaseUrl(process.env[API_BASE_ENV_NAME], {
    allowRemoteHttps: process.env.NODE_ENV === "production"
  });
}
