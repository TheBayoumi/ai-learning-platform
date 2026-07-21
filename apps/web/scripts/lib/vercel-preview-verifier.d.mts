export interface VerificationInput {
  expectedSha: string;
  repository: string;
  branch: string;
  projectId: string;
  teamId: string;
  githubToken: string;
  vercelApiToken: string;
  bypassSecret: string;
  httpTimeoutMs?: number;
  polling?: {
    maximum_duration_ms?: number;
    initial_interval_ms?: number;
    maximum_interval_ms?: number;
    backoff_multiplier?: number;
  };
}

export interface VerificationDependencies {
  fetchImpl?: typeof fetch;
  sleep?: (milliseconds: number) => Promise<void>;
  now?: () => number;
}

export class VerifierError extends Error {
  readonly kind: string;
  readonly exitCode: number;
  readonly details: Readonly<Record<string, unknown>>;
}

export const EXIT_CODES: Readonly<Record<string, number>>;

export interface VerificationEvidence {
  schema_version: number;
  phase: string;
  blocker_id: string;
  result: string;
  verified_at: string;
  expected: Record<string, unknown>;
  discovery: Record<string, unknown>;
  deployment: {
    deployment_id: string;
    git_sha: string;
    ready_state: string;
    target: string | null;
    [key: string]: unknown;
  };
  http: {
    status: number;
    redirect_chain: number[];
    [key: string]: unknown;
  };
  semantics: {
    api_state: string;
    [key: string]: unknown;
  };
  confidentiality: {
    forbidden_markers_absent: boolean;
    assets_scanned: number;
    [key: string]: unknown;
  };
}

export function verifyVercelPreview(
  input: VerificationInput,
  dependencies?: VerificationDependencies
): Promise<VerificationEvidence>;

export function validateEvidence(
  evidence: VerificationEvidence,
  expected?: Pick<
    VerificationInput,
    "expectedSha" | "repository" | "branch" | "projectId" | "teamId"
  >
): true;

export function verifyPageSemantics(
  html: string
): Readonly<Record<string, unknown>>;

export function extractStaticAssets(html: string, pageUrl: string): string[];
