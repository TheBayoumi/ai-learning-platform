import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const BUILD_TOOLCHAIN = Object.freeze({
  localNode: "24.18.0",
  vercelNodeMajor: 24,
  nodeEngine: "24.x",
  npm: "11.18.0",
  packageManager: "npm@11.18.0",
  lockfileVersion: 3,
  next: "16.2.10"
});

export class BuildToolchainContractError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "BuildToolchainContractError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new BuildToolchainContractError(code, message);
}

function parseJson(text, label) {
  try {
    return JSON.parse(text);
  } catch {
    fail("invalid_json", `${label} must contain valid JSON.`);
  }
}

function normalizedObject(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : null;
}

function sameJson(left, right) {
  return JSON.stringify(left ?? {}) === JSON.stringify(right ?? {});
}

function normalizeNodeVersion(value) {
  if (typeof value !== "string") {
    fail("runtime_node", "The Node runtime version is unavailable.");
  }
  const normalized = value.startsWith("v") ? value.slice(1) : value;
  if (!/^\d+\.\d+\.\d+$/.test(normalized)) {
    fail("runtime_node", "The Node runtime version is malformed.");
  }
  return normalized;
}

function npmVersionFromUserAgent(userAgent) {
  if (typeof userAgent !== "string") {
    return null;
  }
  const match = /(?:^|\s)npm\/(\d+\.\d+\.\d+)(?:\s|$)/.exec(userAgent);
  return match?.[1] ?? null;
}

function classifyNpmSource(npmExecPath) {
  if (typeof npmExecPath !== "string" || npmExecPath.length === 0) {
    return "injected";
  }
  return /corepack/i.test(npmExecPath)
    ? "corepack"
    : "npm-execpath";
}

function requireIntegrityBoundLockfile(lockfile) {
  if (lockfile.lockfileVersion !== BUILD_TOOLCHAIN.lockfileVersion) {
    fail("lockfile_version", "package-lock.json must use lockfile version 3.");
  }
  const packages = normalizedObject(lockfile.packages);
  if (!packages || !normalizedObject(packages[""])) {
    fail("lockfile_graph", "package-lock.json must contain a root package entry.");
  }
  for (const [path, record] of Object.entries(packages)) {
    if (path === "") {
      continue;
    }
    if (!normalizedObject(record) || typeof record.version !== "string") {
      fail("lockfile_graph", "Every installed lockfile package must have a version.");
    }
    if (
      typeof record.resolved !== "string" ||
      !record.resolved.startsWith("https://") ||
      typeof record.integrity !== "string" ||
      !/^sha512-[A-Za-z0-9+/]+={0,2}$/.test(record.integrity)
    ) {
      fail("lockfile_integrity", "Every installed lockfile package must be integrity-bound.");
    }
  }
  return packages;
}

export function validateRepositoryContract(source) {
  if (!source || typeof source !== "object") {
    fail("missing_file", "Build-toolchain source files are required.");
  }
  for (const field of ["nvmrc", "npmrc", "packageJson", "packageLock"]) {
    if (typeof source[field] !== "string") {
      fail("missing_file", `Required build-toolchain source ${field} is missing.`);
    }
  }
  if (!/^\d+\.\d+\.\d+\r?\n?$/.test(source.nvmrc)) {
    fail("nvmrc", ".nvmrc must contain one exact Node version and an optional final newline.");
  }
  const nvmrc = source.nvmrc.replace(/\r?\n$/, "");
  if (nvmrc !== BUILD_TOOLCHAIN.localNode) {
    fail("nvmrc", `.nvmrc must contain exactly ${BUILD_TOOLCHAIN.localNode}.`);
  }

  const npmLines = source.npmrc
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#") && !line.startsWith(";"));
  if (npmLines.length !== 1 || npmLines[0] !== "engine-strict=true") {
    fail("npmrc", ".npmrc must contain only strict engine enforcement.");
  }

  const packageJson = parseJson(source.packageJson, "package.json");
  const lockfile = parseJson(source.packageLock, "package-lock.json");
  if (packageJson.packageManager !== BUILD_TOOLCHAIN.packageManager) {
    fail("package_manager", `packageManager must be ${BUILD_TOOLCHAIN.packageManager}.`);
  }
  if (packageJson.engines?.node !== BUILD_TOOLCHAIN.nodeEngine) {
    fail("node_engine", `engines.node must be ${BUILD_TOOLCHAIN.nodeEngine}.`);
  }
  if (packageJson.engines?.npm !== BUILD_TOOLCHAIN.npm) {
    fail("npm_engine", `engines.npm must be ${BUILD_TOOLCHAIN.npm}.`);
  }
  if (packageJson.dependencies?.next !== BUILD_TOOLCHAIN.next) {
    fail("next_version", `Next.js must remain exactly ${BUILD_TOOLCHAIN.next}.`);
  }

  const packages = requireIntegrityBoundLockfile(lockfile);
  const root = packages[""];
  for (const field of ["name", "version", "dependencies", "devDependencies", "engines"]) {
    if (!sameJson(root[field], packageJson[field])) {
      fail("lockfile_root", `package-lock.json root metadata differs at ${field}.`);
    }
  }

  return Object.freeze({
    nvmrc,
    nodeEngine: packageJson.engines.node,
    npmEngine: packageJson.engines.npm,
    packageManager: packageJson.packageManager,
    lockfileVersion: lockfile.lockfileVersion,
    nextVersion: packageJson.dependencies.next,
    packageLockSha256: createHash("sha256").update(source.packageLock).digest("hex")
  });
}

export function validateRuntimeContract(repository, runtime) {
  const node = normalizeNodeVersion(runtime.nodeVersion);
  const npm = runtime.npmVersion ?? npmVersionFromUserAgent(runtime.npmConfigUserAgent);
  if (npm !== BUILD_TOOLCHAIN.npm) {
    fail("runtime_npm", `npm must be exactly ${BUILD_TOOLCHAIN.npm}.`);
  }

  const isVercel = runtime.isVercel === true;
  const nodeMajor = Number(node.split(".")[0]);
  if (isVercel ? nodeMajor !== BUILD_TOOLCHAIN.vercelNodeMajor : node !== repository.nvmrc) {
    fail(
      "runtime_node",
      isVercel
        ? `Vercel must use Node ${BUILD_TOOLCHAIN.vercelNodeMajor}.x.`
        : `Local and CI builds must use Node ${repository.nvmrc}.`
    );
  }

  const lifecycle = runtime.lifecycleEvent ?? "direct";
  const npmCommand = runtime.npmCommand ?? null;
  if (lifecycle === "preinstall" && npmCommand !== "ci") {
    fail("install_command", "Dependency installation must run through npm ci.");
  }
  if (
    ["prebuild", "postbuild"].includes(lifecycle) &&
    !["run", "run-script"].includes(npmCommand)
  ) {
    fail("build_command", "Production build lifecycle must run through npm run build.");
  }

  const npmSource = classifyNpmSource(runtime.npmExecPath);
  if (isVercel && npmSource !== "corepack") {
    fail("npm_source", "Vercel must select the exact npm version through Corepack.");
  }

  return Object.freeze({
    node,
    npm,
    environment: isVercel ? "vercel" : runtime.isCi === true ? "ci" : "local",
    lifecycle,
    npmSource,
    installCommand: lifecycle === "preinstall" ? "npm ci" : null
  });
}

export async function readRepositoryContract(projectRoot) {
  const root = resolve(projectRoot);
  const [nvmrc, npmrc, packageJson, packageLock] = await Promise.all([
    readFile(resolve(root, "..", "..", ".nvmrc"), "utf8"),
    readFile(resolve(root, ".npmrc"), "utf8"),
    readFile(resolve(root, "package.json"), "utf8"),
    readFile(resolve(root, "package-lock.json"), "utf8")
  ]).catch(() => fail("missing_file", "A required build-toolchain file is missing."));
  return validateRepositoryContract({ nvmrc, npmrc, packageJson, packageLock });
}

export async function verifyBuildToolchain(options = {}) {
  const projectRoot =
    options.projectRoot ?? resolve(fileURLToPath(new URL("../../", import.meta.url)));
  const repository = options.repository ?? (await readRepositoryContract(projectRoot));
  const environment = options.environment ?? process.env;
  const runtime = validateRuntimeContract(repository, {
    nodeVersion: options.nodeVersion ?? process.version,
    npmVersion: options.npmVersion,
    npmConfigUserAgent: options.npmConfigUserAgent ?? environment.npm_config_user_agent,
    npmExecPath: options.npmExecPath ?? environment.npm_execpath,
    npmCommand: options.npmCommand ?? environment.npm_command,
    lifecycleEvent: options.lifecycleEvent ?? environment.npm_lifecycle_event,
    isVercel: options.isVercel ?? environment.VERCEL === "1",
    isCi:
      options.isCi ??
      (environment.CI === "true" || environment.GITHUB_ACTIONS === "true")
  });
  return Object.freeze({
    schema_version: 1,
    contract: "f04.build-toolchain",
    result: "PASSED",
    node: runtime.node,
    npm: runtime.npm,
    environment: runtime.environment,
    lifecycle: runtime.lifecycle,
    npm_source: runtime.npmSource,
    install_command: runtime.installCommand,
    lockfile_version: repository.lockfileVersion,
    package_lock_sha256: repository.packageLockSha256,
    next_version: repository.nextVersion
  });
}
