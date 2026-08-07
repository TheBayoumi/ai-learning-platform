import { afterEach, describe, expect, it, vi } from "vitest";

import manifest from "../app/manifest";
import robots from "../app/robots";
import sitemap from "../app/sitemap";
import { readSiteUrl } from "../server/config/site-url";
import { BROWSER_SECURITY_HEADERS } from "../server/security/headers";

const DEFAULT_SITE_URL = "https://web-three-henna-34.vercel.app/";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("publish-ready metadata surface", () => {
  it("uses the verified production URL by default", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    expect(readSiteUrl().toString()).toBe(DEFAULT_SITE_URL);
  });

  it("normalizes a configured site URL to its origin", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://learn.example.com/path/");
    expect(readSiteUrl().toString()).toBe("https://learn.example.com/");
  });

  it.each([
    "not-a-url",
    "https://user:secret@example.com",
    "https://example.com/?secret=value",
    "https://example.com/#fragment"
  ])("rejects unsafe public site URLs: %s", (value) => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", value);
    expect(() => readSiteUrl()).toThrow(/NEXT_PUBLIC_SITE_URL/);
  });

  it("publishes only public pages in the sitemap and blocks API crawling", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    expect(sitemap().map((entry) => entry.url)).toEqual([
      `${DEFAULT_SITE_URL}`,
      `${DEFAULT_SITE_URL}privacy`,
      `${DEFAULT_SITE_URL}terms`,
      `${DEFAULT_SITE_URL}status`
    ]);
    expect(robots()).toEqual({
      rules: { userAgent: "*", allow: "/", disallow: ["/api/"] },
      sitemap: `${DEFAULT_SITE_URL}sitemap.xml`
    });
  });

  it("publishes an installable manifest without external assets", () => {
    expect(manifest()).toMatchObject({
      name: "Career Atlas",
      short_name: "Career Atlas",
      start_url: "/",
      display: "standalone",
      icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }]
    });
  });
});

describe("browser security headers", () => {
  it("defines each required header exactly once", () => {
    const headers = new Map(BROWSER_SECURITY_HEADERS.map((header) => [header.key, header.value]));
    expect(headers.size).toBe(BROWSER_SECURITY_HEADERS.length);
    expect(headers.get("X-Content-Type-Options")).toBe("nosniff");
    expect(headers.get("X-Frame-Options")).toBe("DENY");
    expect(headers.get("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
    expect(headers.get("Cross-Origin-Opener-Policy")).toBe("same-origin");
    expect(headers.get("Strict-Transport-Security")).toContain("max-age=63072000");
  });

  it("blocks framing, plugins, foreign connections, media, and form exfiltration", () => {
    const csp = BROWSER_SECURITY_HEADERS.find(
      (header) => header.key === "Content-Security-Policy"
    )?.value;
    expect(csp).toBeDefined();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("connect-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("form-action 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("media-src 'none'");
    expect(csp).toContain("upgrade-insecure-requests");
  });
});
