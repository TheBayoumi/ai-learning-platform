export class VercelResourceMeasurementError extends Error {
  readonly code: string;
  constructor(code: string, message: string);
}

export interface ResourceMeasurementInput {
  expectedSha: string;
  repository: string;
  branch: string;
  projectId: string;
  teamId: string;
  githubToken: string;
  vercelApiToken: string;
  bypassSecret: string;
  packageLockSha256: string;
  polling?: Record<string, number>;
  quiescenceMs?: number;
  warmSampleCount?: number;
  warmIntervalMs?: number;
}

export interface ResourceLatencySample {
  ttfb_ms: number;
  total_ms: number;
  status: number;
  body_bytes: number;
  cache: string;
  edge_region: string;
}

export interface VercelResourceMeasurementEvidence {
  schema_version: number;
  phase: string;
  blocker_id: string;
  result: string;
  verified_at: string;
  expected_git_sha: string;
  deployment: {
    deployment_id: string;
    created_at: string;
    ready_at: string;
    regions: string[];
  };
  build: {
    duration_ms: number;
    deployment_elapsed_ms: number;
    clone_ms: number;
    install_ms: number;
    compile_ms: number;
    typecheck_ms: number;
    static_generation_ms: number;
    machine_cores: number;
    machine_memory_mb: number;
    vercel_cli: string;
  };
  artifact_footprint: {
    browser_build_files: number;
    browser_build_bytes: number;
    deployed_html_bytes: number;
    deployed_asset_count: number;
    deployed_asset_bytes: number;
    deployed_total_bytes: number;
  };
  cache: {
    restored: boolean;
    created_ms: number;
    uploaded_bytes: number;
    upload_ms: number;
    causal_speedup_claimed: boolean;
  };
  latency: {
    classification: string;
    quiescence_ms: number;
    cold: ResourceLatencySample;
    warm_samples: ResourceLatencySample[];
    warm_ttfb_median_ms: number;
    warm_total_median_ms: number;
    warm_total_p95_ms: number;
    infrastructure_cold_start_claimed: boolean;
  };
  runtime: { node: string; npm: string; next: string };
  cost_observation: {
    team_plan: string;
    preview_deployments_observed: number;
    measurement_http_requests: number;
    build_duration_ms: number;
    cache_upload_bytes: number;
    dollar_estimate_provided: boolean;
    bounded: boolean;
  };
  assertions: Record<string, boolean>;
}

export function packageLockSha256(text: string): string;
export function validateResourceMeasurementEvidence(
  evidence: VercelResourceMeasurementEvidence,
  expected?: { expectedSha?: string; deploymentId?: string }
): true;
export function verifyVercelResourceMeasurements(
  input: ResourceMeasurementInput,
  dependencies?: Record<string, unknown>
): Promise<VercelResourceMeasurementEvidence>;
