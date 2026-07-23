const FORBIDDEN_LITERAL_MARKERS = Object.freeze([
  "web.health.request.completed",
  "ai-learning-platform-web.health",
  "Invalid bounded web health diagnostic completion.",
  "AI_PLATFORM_API_BASE_URL",
  "http://127.0.0.1:8000",
  "/health/live",
  "VERCEL_AUTOMATION_BYPASS_SECRET",
  "VERCEL_API_TOKEN"
]);

const TRACEPARENT_PATTERN = /\b(?!ff)[0-9a-f]{2}-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})\b/gi;
const ALL_ZERO_TRACE_ID = "0".repeat(32);
const ALL_ZERO_PARENT_ID = "0".repeat(16);

export class BrowserConfidentialityError extends Error {
  constructor(issues) {
    super(
      `Browser confidentiality check failed with ${issues.length} issue${
        issues.length === 1 ? "" : "s"
      }.`
    );
    this.name = "BrowserConfidentialityError";
    this.issues = Object.freeze([...issues]);
  }
}

export function scanBrowserText(
  text,
  { sourceLabel = "browser content", secretValues = [] } = {}
) {
  if (typeof text !== "string") {
    throw new TypeError("Browser content must be a string.");
  }
  if (!Array.isArray(secretValues)) {
    throw new TypeError("Secret values must be an array.");
  }

  const issues = [];
  for (const marker of FORBIDDEN_LITERAL_MARKERS) {
    if (text.includes(marker)) {
      issues.push({ code: "forbidden-marker", marker, source: sourceLabel });
    }
  }

  for (const match of text.matchAll(TRACEPARENT_PATTERN)) {
    const [, traceId, parentId] = match;
    if (traceId !== ALL_ZERO_TRACE_ID && parentId !== ALL_ZERO_PARENT_ID) {
      issues.push({
        code: "trace-context",
        marker: "valid-traceparent",
        source: sourceLabel
      });
    }
  }

  secretValues.forEach((value, index) => {
    if (typeof value !== "string" || value.length === 0) {
      return;
    }
    if (text.includes(value)) {
      issues.push({
        code: "secret-value",
        marker: `secret-value-${index + 1}`,
        source: sourceLabel
      });
    }
  });

  if (issues.length > 0) {
    throw new BrowserConfidentialityError(issues);
  }

  return Object.freeze({ source: sourceLabel, scanned_bytes: Buffer.byteLength(text) });
}

export const browserConfidentialityRules = Object.freeze({
  forbidden_literal_markers: FORBIDDEN_LITERAL_MARKERS,
  rejects_valid_traceparent: true,
  scans_supplied_secret_values: true
});
