import { createHash } from "node:crypto";

import { discoverAndValidateExactDeployment } from "./vercel-preview-verifier.mjs";
import { checkVercelProjectBuildConfig } from "./vercel-project-build-config.mjs";

const MAX_EVENTS = 2_000;
const MAX_LOG_BYTES = 1024 * 1024;
const SOURCE_KEYS = Object.freeze([
  ".nvmrc",
  "apps/web/.npmrc",
  "apps/web/package.json",
  "apps/web/package-lock.json",
  "apps/web/vercel.json",
  "plans/F04-vercel-project-build-config.json",
  "apps/web/scripts/lib/build-toolchain-contract.mjs",
  "apps/web/scripts/lib/vercel-build-reproducibility-verifier.mjs"
]);
const EVIDENCE_KEYS = Object.freeze([
  "schema_version",
  "phase",
  "blocker_id",
  "result",
  "verified_at",
  "expected_git_sha",
  "source_hashes",
  "repository_contract",
  "vercel_project",
  "deployment",
  "build_assertions"
]);
const ASSERTION_KEYS = Object.freeze([
  "exact_deployment_bound",
  "project_manifest_matched",
  "corepack_selected",
  "locked_install",
  "lockfile_unchanged",
  "engine_warning_absent",
  "node_major_warning_absent",
  "fallback_absent",
  "production_build_passed",
  "confidentiality_scan_passed"
]);
const REPOSITORY_CONTRACT_KEYS = Object.freeze([
  "nvmrc",
  "node_engine",
  "package_manager",
  "npm_engine",
  "lockfile_version",
  "package_lock_sha256",
  "install_command",
  "build_command",
  "next_version"
]);
const PROJECT_EVIDENCE_KEYS = Object.freeze([
  "project_id",
  "team_id",
  "name",
  "root_directory",
  "framework",
  "node_setting",
  "production_branch",
  "git_repository",
  "install_command",
  "build_command",
  "configuration_matches_manifest"
]);
const DEPLOYMENT_EVIDENCE_KEYS = Object.freeze([
  "deployment_id",
  "git_sha",
  "git_branch",
  "repository",
  "state",
  "target",
  "observed_node",
  "observed_npm"
]);

export class VercelBuildReproducibilityError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "VercelBuildReproducibilityError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new VercelBuildReproducibilityError(code, message);
}

function assertExactKeys(value, expected, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    fail("evidence", `${label} must be an object.`);
  }
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
    fail("evidence", `${label} fields do not match the safe schema.`);
  }
}

export function hashBuildEvidenceSources(sourceFiles) {
  assertExactKeys(sourceFiles, SOURCE_KEYS, "Build evidence sources");
  return Object.fromEntries(
    SOURCE_KEYS.map((path) => {
      const value = sourceFiles[path];
      if (typeof value !== "string") {
        fail("source", `Build evidence source ${path} is missing.`);
      }
      return [path, createHash("sha256").update(value).digest("hex")];
    })
  );
}

async function requestEvents(fetchImpl, token, deploymentId, teamId) {
  if (typeof token !== "string" || token.length === 0) {
    fail("configuration", "VERCEL_API_TOKEN is required.");
  }
  let response;
  try {
    response = await fetchImpl(
      `https://api.vercel.com/v2/deployments/${deploymentId}/events?teamId=${encodeURIComponent(teamId)}`,
      {
        headers: { authorization: `Bearer ${token}` },
        redirect: "manual"
      }
    );
  } catch {
    fail("logs", "Vercel build-log request failed.");
  }
  if (!response.ok) {
    fail("logs", `Vercel build-log request returned HTTP ${response.status}.`);
  }
  const text = await response.text();
  if (Buffer.byteLength(text) > MAX_LOG_BYTES) {
    fail("logs", "Vercel build-log response exceeded the size limit.");
  }
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    fail("logs", "Vercel build-log response was not valid JSON.");
  }
  if (!Array.isArray(payload) || payload.length === 0 || payload.length > MAX_EVENTS) {
    fail("logs", "Vercel build-log response is missing or unbounded.");
  }
  return payload;
}

function normalizeLogs(events, expectedDeploymentId) {
  let aggregate = 0;
  const normalized = events.map((event, index) => {
    if (
      !Number.isFinite(event?.created) ||
      event?.payload?.deploymentId !== expectedDeploymentId ||
      typeof event?.payload?.text !== "string"
    ) {
      fail("logs", "A Vercel build event is malformed or belongs to another deployment.");
    }
    const text = event.payload.text.replace(/\u001b\[[0-9;]*m/g, "").trim();
    aggregate += Buffer.byteLength(text);
    if (aggregate > MAX_LOG_BYTES) {
      fail("logs", "Normalized Vercel build logs exceeded the size limit.");
    }
    return {
      index,
      created: event.created,
      serial: Number(event.payload.serial ?? index),
      text
    };
  });
  if (normalized.some(({ serial }) => !Number.isFinite(serial))) {
    fail("logs", "A Vercel build-event serial is malformed.");
  }
  normalized.sort((left, right) => left.created - right.created || left.serial - right.serial);
  for (let index = 1; index < normalized.length; index += 1) {
    if (
      normalized[index].created === normalized[index - 1].created &&
      normalized[index].serial === normalized[index - 1].serial
    ) {
      fail("logs", "Vercel build-event ordering is ambiguous.");
    }
  }
  return normalized.map((log, index) => ({ ...log, index }));
}

function parseToolchainMarkers(logs, expectedLockHash) {
  const markers = [];
  for (const log of logs) {
    if (!log.text.startsWith("{")) {
      continue;
    }
    let value;
    try {
      value = JSON.parse(log.text);
    } catch {
      continue;
    }
    if (value?.contract === "f04.build-toolchain") {
      markers.push({ ...value, logIndex: log.index });
    }
  }
  const expectedLifecycles = ["preinstall", "prebuild", "postbuild"];
  if (markers.length !== expectedLifecycles.length) {
    fail("logs", "Build logs must contain exactly three toolchain contract records.");
  }
  for (let index = 0; index < expectedLifecycles.length; index += 1) {
    const marker = markers[index];
    const lifecycle = expectedLifecycles[index];
    if (
      marker.schema_version !== 1 ||
      marker.result !== "PASSED" ||
      marker.lifecycle !== lifecycle ||
      marker.environment !== "vercel" ||
      marker.npm !== "11.18.0" ||
      !/^24\.\d+\.\d+$/.test(marker.node) ||
      marker.npm_source !== "corepack" ||
      marker.lockfile_version !== 3 ||
      marker.next_version !== "16.2.10" ||
      marker.package_lock_sha256 !== expectedLockHash ||
      marker.install_command !== (lifecycle === "preinstall" ? "npm ci" : null) ||
      (index > 0 && marker.logIndex <= markers[index - 1].logIndex)
    ) {
      fail("logs", `The ${lifecycle} toolchain record does not prove the expected contract.`);
    }
  }
  return markers;
}

function requireLog(logs, predicate, message) {
  if (!logs.some(({ text }) => predicate(text))) {
    fail("logs", message);
  }
}

function rejectLog(logs, pattern, message) {
  if (logs.some(({ text }) => pattern.test(text))) {
    fail("logs", message);
  }
}

function validateBuildLogs(logs, expectedLockHash) {
  const markers = parseToolchainMarkers(logs, expectedLockHash);
  requireLog(logs, (text) => text.includes("npm ci"), "Build logs do not show npm ci.");
  requireLog(
    logs,
    (text) => text === 'Running "npm run build"',
    "Build logs do not show the committed production build command."
  );
  requireLog(
    logs,
    (text) => text === "Detected Next.js version: 16.2.10",
    "Build logs do not prove the exact Next.js version."
  );
  requireLog(logs, (text) => text.includes("Compiled successfully"), "Next.js compilation did not pass.");
  requireLog(
    logs,
    (text) => text.startsWith("Browser confidentiality check passed:"),
    "Browser confidentiality scan did not pass."
  );
  requireLog(logs, (text) => text.includes("Build Completed"), "Vercel build did not complete.");
  requireLog(logs, (text) => text === "Deployment completed", "Vercel deployment did not complete.");
  rejectLog(logs, /EBADENGINE/i, "Build logs contain EBADENGINE.");
  rejectLog(
    logs,
    /automatically upgrade when a new major Node\.js Version is released/i,
    "Build logs contain the broad Node-major warning."
  );
  rejectLog(
    logs,
    /npm (?:install|i) (?:--global|-g) npm@|corepack (?:prepare|use)/i,
    "Build logs contain an unapproved package-manager fallback."
  );
  rejectLog(logs, /Running "npm install"/i, "Build logs used npm install instead of npm ci.");
  return markers;
}

function assertEvidenceSafe(evidence, secretValues = []) {
  const serialized = JSON.stringify(evidence);
  const forbidden = [
    /authorization/i,
    /cookie/i,
    /bearer\s/i,
    /x-vercel-protection/i,
    /"[^"]*(?:token|secret|password|credential)[^"]*"\s*:/i,
    /https?:\/\//i
  ];
  if (forbidden.some((pattern) => pattern.test(serialized))) {
    fail("confidentiality", "Sanitized build evidence contains forbidden material.");
  }
  for (const secret of secretValues) {
    if (typeof secret === "string" && secret.length > 0 && serialized.includes(secret)) {
      fail("confidentiality", "Sanitized build evidence contains a credential value.");
    }
  }
}

export function validateBuildReproducibilityEvidence(evidence, expected = {}) {
  assertExactKeys(evidence, EVIDENCE_KEYS, "Build reproducibility evidence");
  assertExactKeys(evidence.source_hashes, SOURCE_KEYS, "Build reproducibility source hashes");
  assertExactKeys(
    evidence.repository_contract,
    REPOSITORY_CONTRACT_KEYS,
    "Repository contract evidence"
  );
  assertExactKeys(evidence.vercel_project, PROJECT_EVIDENCE_KEYS, "Vercel project evidence");
  assertExactKeys(evidence.deployment, DEPLOYMENT_EVIDENCE_KEYS, "Deployment evidence");
  assertExactKeys(evidence.build_assertions, ASSERTION_KEYS, "Build assertions");
  const expectedSourceHashes = expected.sourceHashes;
  if (
    expectedSourceHashes &&
    SOURCE_KEYS.some(
      (path) => evidence.source_hashes[path] !== expectedSourceHashes[path]
    )
  ) {
    fail("evidence", "Build evidence source hashes differ from the checked-out source.");
  }
  const expectedSha = expected.expectedSha ?? evidence.expected_git_sha;
  const expectedRepository = expected.repository ?? "TheBayoumi/ai-learning-platform";
  const expectedBranch = expected.branch ?? "automation/f04-vercel-deployment-baseline";
  const expectedProjectId = expected.projectId ?? "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN";
  const expectedTeamId = expected.teamId ?? "team_bZWPrEPMa4sBoWU7syo3ZIRZ";
  const expectedDeploymentId = expected.deploymentId ?? evidence.deployment?.deployment_id;
  if (
    evidence.schema_version !== 1 ||
    evidence.phase !== "F04" ||
    evidence.blocker_id !== "f04.build_reproducibility" ||
    evidence.result !== "PASSED" ||
    !Number.isFinite(Date.parse(evidence.verified_at)) ||
    !/^[0-9a-f]{40}$/.test(evidence.expected_git_sha) ||
    evidence.expected_git_sha !== expectedSha ||
    evidence.deployment?.git_sha !== expectedSha ||
    !/^dpl_[A-Za-z0-9]+$/.test(evidence.deployment?.deployment_id) ||
    evidence.deployment?.deployment_id !== expectedDeploymentId ||
    evidence.deployment?.git_branch !== expectedBranch ||
    evidence.deployment?.repository !== expectedRepository ||
    evidence.deployment?.state !== "READY" ||
    ![null, "preview"].includes(evidence.deployment?.target) ||
    !/^24\.\d+\.\d+$/.test(evidence.deployment?.observed_node) ||
    evidence.deployment?.observed_npm !== "11.18.0" ||
    evidence.vercel_project?.project_id !== expectedProjectId ||
    evidence.vercel_project?.team_id !== expectedTeamId ||
    evidence.vercel_project?.name !== "web" ||
    evidence.vercel_project?.root_directory !== "apps/web" ||
    evidence.vercel_project?.framework !== "nextjs" ||
    evidence.vercel_project?.node_setting !== "24.x" ||
    evidence.vercel_project?.production_branch !== "main" ||
    evidence.vercel_project?.git_repository !== expectedRepository ||
    evidence.vercel_project?.install_command !== "npm ci" ||
    evidence.vercel_project?.build_command !== "npm run build" ||
    evidence.vercel_project?.configuration_matches_manifest !== true ||
    evidence.repository_contract?.nvmrc !== "24.18.0" ||
    evidence.repository_contract?.node_engine !== "24.x" ||
    evidence.repository_contract?.package_manager !== "npm@11.18.0" ||
    evidence.repository_contract?.npm_engine !== "11.18.0" ||
    evidence.repository_contract?.lockfile_version !== 3 ||
    evidence.repository_contract?.package_lock_sha256 !==
      evidence.source_hashes["apps/web/package-lock.json"] ||
    evidence.repository_contract?.install_command !== "npm ci" ||
    evidence.repository_contract?.build_command !== "npm run build" ||
    evidence.repository_contract?.next_version !== "16.2.10" ||
    !Object.values(evidence.source_hashes).every((hash) => /^[0-9a-f]{64}$/.test(hash)) ||
    !Object.values(evidence.build_assertions ?? {}).every((value) => value === true)
  ) {
    fail("evidence", "Build reproducibility evidence does not prove the required contract.");
  }
  assertEvidenceSafe(evidence);
  return true;
}

export async function verifyVercelBuildReproducibility(input, dependencies = {}) {
  const sourceHashes = hashBuildEvidenceSources(input.sourceFiles);
  const exactDeployment = await discoverAndValidateExactDeployment(
    {
      expectedSha: input.expectedSha,
      repository: input.repository,
      branch: input.branch,
      projectId: input.projectId,
      teamId: input.teamId,
      githubToken: input.githubToken,
      vercelApiToken: input.vercelApiToken,
      polling: input.polling
    },
    dependencies
  );
  const project = await checkVercelProjectBuildConfig(input.projectManifest, {
    fetchImpl: dependencies.fetchImpl ?? globalThis.fetch,
    token: input.vercelApiToken
  });
  const events = await requestEvents(
    dependencies.fetchImpl ?? globalThis.fetch,
    input.vercelApiToken,
    exactDeployment.deployment.deployment_id,
    input.teamId
  );
  const logs = normalizeLogs(events, exactDeployment.deployment.deployment_id);
  const markers = validateBuildLogs(logs, sourceHashes["apps/web/package-lock.json"]);
  const finalMarker = markers.at(-1);
  const evidence = {
    schema_version: 1,
    phase: "F04",
    blocker_id: "f04.build_reproducibility",
    result: "PASSED",
    verified_at: new Date(exactDeployment.runtime.now()).toISOString(),
    expected_git_sha: input.expectedSha,
    source_hashes: sourceHashes,
    repository_contract: {
      nvmrc: "24.18.0",
      node_engine: "24.x",
      package_manager: "npm@11.18.0",
      npm_engine: "11.18.0",
      lockfile_version: 3,
      package_lock_sha256: sourceHashes["apps/web/package-lock.json"],
      install_command: "npm ci",
      build_command: "npm run build",
      next_version: "16.2.10"
    },
    vercel_project: {
      project_id: project.project.id,
      team_id: project.project.team_id,
      name: project.project.name,
      root_directory: project.project.root_directory,
      framework: project.project.framework,
      node_setting: project.project.node_version,
      production_branch: project.project.production_branch,
      git_repository: project.project.git_repository,
      install_command: project.project.install_command,
      build_command: project.project.build_command,
      configuration_matches_manifest: true
    },
    deployment: {
      deployment_id: exactDeployment.deployment.deployment_id,
      git_sha: exactDeployment.deployment.git_sha,
      git_branch: exactDeployment.deployment.git_branch,
      repository: input.repository,
      state: exactDeployment.deployment.ready_state,
      target: exactDeployment.deployment.target,
      observed_node: finalMarker.node,
      observed_npm: finalMarker.npm
    },
    build_assertions: {
      exact_deployment_bound: true,
      project_manifest_matched: true,
      corepack_selected: true,
      locked_install: true,
      lockfile_unchanged: true,
      engine_warning_absent: true,
      node_major_warning_absent: true,
      fallback_absent: true,
      production_build_passed: true,
      confidentiality_scan_passed: true
    }
  };
  validateBuildReproducibilityEvidence(evidence, {
    expectedSha: input.expectedSha,
    repository: input.repository,
    branch: input.branch,
    projectId: input.projectId,
    teamId: input.teamId,
    deploymentId: exactDeployment.deployment.deployment_id,
    sourceHashes
  });
  assertEvidenceSafe(evidence, [input.githubToken, input.vercelApiToken]);
  return evidence;
}
