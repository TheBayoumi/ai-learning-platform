import type { VercelProjectBuildManifest } from "./vercel-project-build-config.mjs";

export interface VercelBuildReproducibilityInput {
  expectedSha: string;
  repository: string;
  branch: string;
  projectId: string;
  teamId: string;
  githubToken: string;
  vercelApiToken: string;
  projectManifest: VercelProjectBuildManifest;
  sourceFiles: Record<string, string>;
  polling?: Record<string, number>;
}

export class VercelBuildReproducibilityError extends Error {
  readonly code: string;
}

export function hashBuildEvidenceSources(sourceFiles: Record<string, string>): Record<string, string>;
export function validateBuildReproducibilityEvidence(
  evidence: Record<string, unknown>,
  expected?: {
    expectedSha?: string;
    repository?: string;
    branch?: string;
    projectId?: string;
    teamId?: string;
    deploymentId?: string;
    sourceHashes?: Record<string, string>;
  }
): true;
export function verifyVercelBuildReproducibility(
  input: VercelBuildReproducibilityInput,
  dependencies?: { fetchImpl?: typeof fetch; sleep?: (milliseconds: number) => Promise<void>; now?: () => number }
): Promise<Record<string, unknown>>;
