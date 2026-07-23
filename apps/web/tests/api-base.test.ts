import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it, vi } from "vitest";

import {
  API_BASE_ENV_NAME,
  ApiBaseConfigurationError,
  parseApiBaseUrl,
  readApiBaseUrl
} from "../server/config/api-base";
import { createConfiguredHealthAdapter } from "../server/health/health-adapter";

describe("server API base configuration", () => {
  it("uses the deterministic IPv4 loopback default", () => {
    expect(parseApiBaseUrl(undefined)).toBe("http://127.0.0.1:8000");
  });

  it.each([
    ["http://127.0.0.1:8000", "http://127.0.0.1:8000"],
    ["http://127.0.0.1:65535/", "http://127.0.0.1:65535"],
    ["http://[::1]:8000", "http://[::1]:8000"],
    ["http://[::1]:9000/", "http://[::1]:9000"]
  ])("accepts and normalizes literal loopback origin %s", (input, expected) => {
    expect(parseApiBaseUrl(input)).toBe(expected);
  });

  it("accepts canonical public HTTPS origins only when explicitly enabled", () => {
    expect(
      parseApiBaseUrl("https://api-learning.example.com/", {
        allowRemoteHttps: true
      })
    ).toBe("https://api-learning.example.com");

    for (const input of [
      "http://api-learning.example.com",
      "https://api-learning.example.com:8443",
      "https://localhost",
      "https://service.local",
      "https://127.0.0.1"
    ]) {
      expect(() =>
        parseApiBaseUrl(input, { allowRemoteHttps: true })
      ).toThrow(ApiBaseConfigurationError);
    }
  });

  it.each([
    "",
    " ",
    "http://127.0.0.1:8000 ",
    "/api",
    "not a URL",
    "https://127.0.0.1:8000",
    "ftp://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://[::1]",
    "http://127.0.0.1:08000",
    "HTTP://127.0.0.1:8000",
    "http://127.0.0.1:0",
    "http://127.0.0.1:80",
    "http://127.0.0.1:65536",
    "http://127.000.000.001:8000",
    "http://[0:0:0:0:0:0:0:1]:8000",
    "http://0.0.0.0:8000",
    "http://192.168.1.1:8000",
    "http://example.com:8000",
    "http://2130706433:8000",
    "http://user:password@127.0.0.1:8000",
    "http://127.0.0.1:8000/api",
    "http://127.0.0.1:8000?debug=true",
    "http://127.0.0.1:8000#fragment"
  ])("rejects unsafe or malformed explicit value without echoing it: %s", (input) => {
    expect(() => parseApiBaseUrl(input)).toThrow(ApiBaseConfigurationError);

    try {
      parseApiBaseUrl(input);
    } catch (error) {
      expect(error).toBeInstanceOf(ApiBaseConfigurationError);
      expect((error as Error).message).toBe(
        new ApiBaseConfigurationError().message
      );
    }
  });

  it("reads only the server environment at call time", () => {
    const original = process.env[API_BASE_ENV_NAME];
    try {
      delete process.env[API_BASE_ENV_NAME];
      expect(readApiBaseUrl()).toBe("http://127.0.0.1:8000");

      process.env[API_BASE_ENV_NAME] = "http://[::1]:9000";
      expect(readApiBaseUrl()).toBe("http://[::1]:9000");
    } finally {
      if (original === undefined) {
        delete process.env[API_BASE_ENV_NAME];
      } else {
        process.env[API_BASE_ENV_NAME] = original;
      }
    }
  });

  it("fails configuration before any fetch can run", () => {
    const fetchImplementation = vi.fn<typeof fetch>();

    expect(() =>
      createConfiguredHealthAdapter({
        configuredApiBaseUrl: "https://public.example",
        fetch: fetchImplementation,
        timeoutMs: 2_000
      })
    ).toThrow(ApiBaseConfigurationError);
    expect(fetchImplementation).not.toHaveBeenCalled();
  });

  it("keeps runtime environment access behind a compiler-enforced server boundary", () => {
    const configSource = readFileSync(
      resolve(process.cwd(), "server/config/api-base.ts"),
      "utf8"
    );
    const adapterSource = readFileSync(
      resolve(process.cwd(), "server/health/health-adapter.ts"),
      "utf8"
    );

    expect(configSource).toMatch(/^import "server-only";/u);
    expect(adapterSource).toMatch(/^import "server-only";/u);
    expect(configSource).toContain("process.env[API_BASE_ENV_NAME]");
    expect(configSource).not.toContain("NEXT_PUBLIC_");
    expect(adapterSource).not.toContain("process.env");
  });
});
