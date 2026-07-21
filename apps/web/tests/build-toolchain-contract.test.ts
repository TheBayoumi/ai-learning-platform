import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { beforeAll, describe, expect, it } from "vitest";

import {
  BuildToolchainContractError,
  readRepositoryContract,
  validateRepositoryContract,
  validateRuntimeContract
} from "../scripts/lib/build-toolchain-contract.mjs";

type Source = {
  nvmrc: string;
  npmrc: string;
  repositoryPackageJson: string;
  packageJson: string;
  packageLock: string;
};

type PackageFixture = {
  packageManager?: string;
  engines: { node: string; npm: string };
};

type RepositoryPackageFixture = {
  private?: boolean;
  packageManager?: string;
};

type LockFixture = {
  lockfileVersion: number;
  packages: Record<
    string,
    { integrity?: string; engines?: { node: string; npm?: string }; [key: string]: unknown }
  >;
};

let validSource: Source;

beforeAll(async () => {
  const webRoot = fileURLToPath(new URL("../", import.meta.url));
  validSource = {
    nvmrc: await readFile(new URL("../../../.nvmrc", import.meta.url), "utf8"),
    npmrc: await readFile(new URL("../.npmrc", import.meta.url), "utf8"),
    repositoryPackageJson: await readFile(new URL("../../../package.json", import.meta.url), "utf8"),
    packageJson: await readFile(new URL("../package.json", import.meta.url), "utf8"),
    packageLock: await readFile(new URL("../package-lock.json", import.meta.url), "utf8")
  };
  expect(webRoot).toContain("apps");
});

function mutatePackage(mutator: (value: PackageFixture) => void): Source {
  const value = JSON.parse(validSource.packageJson) as PackageFixture;
  mutator(value);
  return { ...validSource, packageJson: JSON.stringify(value) };
}

function mutateRepositoryPackage(mutator: (value: RepositoryPackageFixture) => void): Source {
  const value = JSON.parse(validSource.repositoryPackageJson) as RepositoryPackageFixture;
  mutator(value);
  return { ...validSource, repositoryPackageJson: JSON.stringify(value) };
}

function mutateLock(mutator: (value: LockFixture) => void): Source {
  const value = JSON.parse(validSource.packageLock) as LockFixture;
  mutator(value);
  return { ...validSource, packageLock: JSON.stringify(value) };
}

describe("build toolchain repository contract", () => {
  it("accepts the exact committed contract and integrity-bound lock graph", () => {
    const result = validateRepositoryContract(validSource);
    expect(result).toMatchObject({
      nvmrc: "24.18.0",
      nodeEngine: "24.x",
      npmEngine: "11.18.0",
      repositoryPackageManager: "npm@11.18.0",
      packageManager: "npm@11.18.0",
      lockfileVersion: 3,
      nextVersion: "16.2.10"
    });
    expect(result.packageLockSha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it.each([
    ["broad Node range", () => mutatePackage((value) => (value.engines.node = ">=20.9.0 <26"))],
    ["broad npm range", () => mutatePackage((value) => (value.engines.npm = ">=11.18.0 <12"))],
    ["missing packageManager", () => mutatePackage((value) => delete value.packageManager)],
    ["packageManager mismatch", () => mutatePackage((value) => (value.packageManager = "npm@11.12.1"))]
  ])("rejects %s", (_label, source) => {
    expect(() => validateRepositoryContract(source())).toThrow(BuildToolchainContractError);
  });

  it.each([
    [
      "missing repository packageManager",
      () => mutateRepositoryPackage((value) => delete value.packageManager)
    ],
    [
      "repository packageManager mismatch",
      () => mutateRepositoryPackage((value) => (value.packageManager = "npm@11.12.1"))
    ],
    [
      "non-private repository manifest",
      () => mutateRepositoryPackage((value) => (value.private = false))
    ]
  ])("rejects %s", (_label, source) => {
    expect(() => validateRepositoryContract(source())).toThrow(/repository package.json/);
  });

  it.each([
    ["missing .nvmrc", { nvmrc: undefined as never }],
    ["malformed .nvmrc", { nvmrc: "24.x\n" }],
    ["padded .nvmrc", { nvmrc: " 24.18.0 \n" }],
    ["wrong Node patch", { nvmrc: "24.17.0\n" }],
    ["missing .npmrc", { npmrc: undefined as never }],
    ["missing repository package.json", { repositoryPackageJson: undefined as never }],
    ["engine strict disabled", { npmrc: "engine-strict=false\n" }],
    ["unsafe extra npm config", { npmrc: "engine-strict=true\nregistry=https://example.invalid\n" }],
    ["missing lockfile", { packageLock: undefined as never }]
  ])("rejects %s", (_label, override) => {
    expect(() => validateRepositoryContract({ ...validSource, ...override })).toThrow(
      BuildToolchainContractError
    );
  });

  it("rejects a lockfile-version mismatch", () => {
    expect(() =>
      validateRepositoryContract(mutateLock((value) => (value.lockfileVersion = 2)))
    ).toThrow(/lockfile version 3/);
  });

  it("rejects package and lock-root metadata disagreement", () => {
    expect(() =>
      validateRepositoryContract(
        mutateLock((value) => (value.packages[""].engines!.node = "25.x"))
      )
    ).toThrow(/root metadata/);
  });

  it("rejects a package without integrity", () => {
    expect(() =>
      validateRepositoryContract(
        mutateLock((value) => delete value.packages["node_modules/react"].integrity)
      )
    ).toThrow(/integrity-bound/);
  });

  it("rejects a missing repository root", async () => {
    await expect(readRepositoryContract("Z:/definitely-missing-f04-web")).rejects.toThrow(
      BuildToolchainContractError
    );
  });
});

describe("build toolchain runtime contract", () => {
  function repository() {
    return validateRepositoryContract(validSource);
  }

  it.each([
    ["local", { nodeVersion: "v24.18.0", npmVersion: "11.18.0" }],
    ["CI", { nodeVersion: "24.18.0", npmConfigUserAgent: "npm/11.18.0 node/v24.18.0", isCi: true }]
  ])("accepts the exact %s toolchain", (_label, runtime) => {
    expect(validateRuntimeContract(repository(), runtime)).toMatchObject({
      node: "24.18.0",
      npm: "11.18.0"
    });
  });

  it("accepts Vercel Node 24 patch variance only through exact Corepack npm", () => {
    expect(
      validateRuntimeContract(repository(), {
        nodeVersion: "v24.15.0",
        npmVersion: "11.18.0",
        npmExecPath: "/vercel/.cache/node/corepack/v1/npm/11.18.0/bin/npm-cli.js",
        isVercel: true,
        lifecycleEvent: "preinstall",
        npmCommand: "ci"
      })
    ).toMatchObject({ npmSource: "corepack", installCommand: "npm ci" });
  });

  it.each([
    ["local Node 25", { nodeVersion: "25.2.1", npmVersion: "11.18.0" }],
    ["local wrong Node patch", { nodeVersion: "24.15.0", npmVersion: "11.18.0" }],
    ["Vercel Node 23", { nodeVersion: "23.11.1", npmVersion: "11.18.0", isVercel: true, npmExecPath: "/corepack/npm-cli.js" }],
    ["Vercel Node 25", { nodeVersion: "25.1.0", npmVersion: "11.18.0", isVercel: true, npmExecPath: "/corepack/npm-cli.js" }],
    ["npm 11.12.1", { nodeVersion: "24.18.0", npmVersion: "11.12.1" }],
    ["npm 11.18.1", { nodeVersion: "24.18.0", npmVersion: "11.18.1" }]
  ])("rejects %s", (_label, runtime) => {
    expect(() => validateRuntimeContract(repository(), runtime)).toThrow(
      BuildToolchainContractError
    );
  });

  it("rejects npm install during preinstall", () => {
    expect(() =>
      validateRuntimeContract(repository(), {
        nodeVersion: "24.18.0",
        npmVersion: "11.18.0",
        lifecycleEvent: "preinstall",
        npmCommand: "install"
      })
    ).toThrow(/npm ci/);
  });

  it("rejects a production build outside npm run build", () => {
    expect(() =>
      validateRuntimeContract(repository(), {
        nodeVersion: "24.18.0",
        npmVersion: "11.18.0",
        lifecycleEvent: "prebuild",
        npmCommand: "ci"
      })
    ).toThrow(/npm run build/);
  });
});
