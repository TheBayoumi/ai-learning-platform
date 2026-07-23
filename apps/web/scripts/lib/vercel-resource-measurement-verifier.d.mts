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

export function packageLockSha256(text: string): string;
export function validateResourceMeasurementEvidence(
  evidence: any,
  expected?: { expectedSha?: string; deploymentId?: string }
): true;
export function verifyVercelResourceMeasurements(
  input: ResourceMeasurementInput,
  dependencies?: Record<string, unknown>
): Promise<any>;
