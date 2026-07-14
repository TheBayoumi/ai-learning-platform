// Generated from apps/api/openapi/health.openapi.json.
// Do not edit by hand. Regenerate from apps/api with:
// uv run --locked python -m ai_learning_platform_api.contracts.health_typescript write openapi/health.openapi.json ../web/server/contracts/generated/health-response.ts

export type HealthResponse = Readonly<{
  readonly detail: string;
  readonly status: "ok";
}>;

export function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    Object.prototype.hasOwnProperty.call(candidate, "detail") && typeof candidate.detail === "string" &&
    Object.prototype.hasOwnProperty.call(candidate, "status") && candidate.status === "ok"
  );
}
