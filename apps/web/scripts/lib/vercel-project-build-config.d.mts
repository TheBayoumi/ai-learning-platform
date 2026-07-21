export interface VercelProjectBuildManifest {
  schema_version: 1;
  project: Record<string, string>;
  build: Record<string, string>;
  environment: {
    ENABLE_EXPERIMENTAL_COREPACK: {
      required: true;
      value: "1";
      targets: ["preview"];
      git_branch: string;
    };
  };
}

export interface VercelConfigDependencies {
  fetchImpl?: typeof fetch;
  token?: string;
}

export class VercelProjectConfigError extends Error {
  readonly code: string;
}

export function validateVercelProjectManifest(
  manifest: VercelProjectBuildManifest
): VercelProjectBuildManifest;
export function checkVercelProjectBuildConfig(
  manifest: VercelProjectBuildManifest,
  dependencies?: VercelConfigDependencies
): Promise<Record<string, unknown>>;
export function applyVercelProjectBuildConfig(
  manifest: VercelProjectBuildManifest,
  confirmation: string,
  dependencies?: VercelConfigDependencies
): Promise<Record<string, unknown>>;
