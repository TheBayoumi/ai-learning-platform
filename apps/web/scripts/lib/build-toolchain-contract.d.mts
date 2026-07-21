export interface RepositoryContractSource {
  nvmrc: string;
  npmrc: string;
  packageJson: string;
  packageLock: string;
}

export interface RepositoryContract {
  nvmrc: string;
  nodeEngine: string;
  npmEngine: string;
  packageManager: string;
  lockfileVersion: number;
  nextVersion: string;
  packageLockSha256: string;
}

export interface RuntimeContractInput {
  nodeVersion: string;
  npmVersion?: string;
  npmConfigUserAgent?: string;
  npmExecPath?: string;
  npmCommand?: string;
  lifecycleEvent?: string;
  isVercel?: boolean;
  isCi?: boolean;
}

export interface BuildToolchainEvidence {
  schema_version: 1;
  contract: "f04.build-toolchain";
  result: "PASSED";
  node: string;
  npm: string;
  environment: "local" | "ci" | "vercel";
  lifecycle: string;
  npm_source: string;
  install_command: "npm ci" | null;
  lockfile_version: 3;
  package_lock_sha256: string;
  next_version: string;
}

export const BUILD_TOOLCHAIN: Readonly<{
  localNode: string;
  vercelNodeMajor: number;
  nodeEngine: string;
  npm: string;
  packageManager: string;
  lockfileVersion: number;
  next: string;
}>;

export class BuildToolchainContractError extends Error {
  readonly code: string;
}

export function validateRepositoryContract(source: RepositoryContractSource): RepositoryContract;
export function validateRuntimeContract(
  repository: RepositoryContract,
  runtime: RuntimeContractInput
): Readonly<Record<string, unknown>>;
export function readRepositoryContract(projectRoot: string): Promise<RepositoryContract>;
export function verifyBuildToolchain(options?: Record<string, unknown>): Promise<BuildToolchainEvidence>;
