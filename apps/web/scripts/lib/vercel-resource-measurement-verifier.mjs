import { createHash } from "node:crypto";

import {
  discoverAndValidateExactDeployment,
  extractStaticAssets,
  verifyPageSemantics
} from "./vercel-preview-verifier.mjs";

const MAX_BUILD_EVENTS = 2_000;
const MAX_BUILD_LOG_BYTES = 1024 * 1024;
const MAX_BUILD_LOG_ATTEMPTS = 12;
const BUILD_LOG_RETRY_MS = 5_000;
const DEFAULT_QUIESCENCE_MS = 60_000;
const DEFAULT_WARM_SAMPLE_COUNT = 5;
const DEFAULT_WARM_INTERVAL_MS = 250;
const HTTP_TIMEOUT_MS = 30_000;
const MAX_PAGE_BYTES = 128 * 1024;
const MAX_ASSET_BYTES = 512 * 1024;
const MAX_ASSET_COUNT = 64;
const MAX_AGGREGATE_ASSET_BYTES = 2 * 1024 * 1024;
const MAX_TEAM_RESPONSE_BYTES = 128 * 1024;
const EVIDENCE_KEYS = Object.freeze([
  "schema_version",
  "phase",
  "blocker_id",
  "result",
  "verified_at",
  "expected_git_sha",
  "deployment",
  "build",
  "artifact_footprint",
  "cache",
  "latency",
  "runtime",
  "cost_observation",
  "assertions"
]);

export class VercelResourceMeasurementError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "VercelResourceMeasurementError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new VercelResourceMeasurementError(code, message);
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

function requireFinite(value, label, minimum = 0, maximum = Number.MAX_SAFE_INTEGER) {
  if (!Number.isFinite(value) || value < minimum || value > maximum) {
    fail("measurement", `${label} is outside the bounded range.`);
  }
  return value;
}

async function requestBuildEvents(fetchImpl, token, deploymentId, teamId) {
  const parameters = new URLSearchParams({
    direction: "forward",
    follow: "0",
    limit: String(MAX_BUILD_EVENTS),
    teamId
  });
  let response;
  try {
    response = await fetchImpl(
      `https://api.vercel.com/v3/deployments/${encodeURIComponent(deploymentId)}/events?${parameters.toString()}`,
      { headers: { authorization: `Bearer ${token}` }, redirect: "manual" }
    );
  } catch {
    fail("logs_pending", "Vercel build-log request failed.");
  }
  if (!response.ok) {
    if ([404, 409, 429].includes(response.status) || response.status >= 500) {
      fail("logs_pending", `Vercel build-log request returned HTTP ${response.status}.`);
    }
    fail("logs", `Vercel build-log request returned HTTP ${response.status}.`);
  }
  const text = await response.text();
  if (Buffer.byteLength(text) > MAX_BUILD_LOG_BYTES) {
    fail("logs", "Vercel build-log response exceeded the size limit.");
  }
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    fail("logs", "Vercel build-log response was not valid JSON.");
  }
  if (!Array.isArray(payload) || payload.length === 0 || payload.length > MAX_BUILD_EVENTS) {
    fail("logs_pending", "Vercel build-log response is missing or unbounded.");
  }
  return payload;
}

function normalizeBuildLogs(events, deploymentId) {
  let aggregateBytes = 0;
  const logs = [];
  for (const [index, event] of events.entries()) {
    const payload =
      event?.payload && typeof event.payload === "object" && !Array.isArray(event.payload)
        ? event.payload
        : event;
    if (payload?.deploymentId !== deploymentId) {
      fail("logs", "A Vercel build event belongs to another deployment.");
    }
    if (payload.text === undefined) {
      continue;
    }
    if (typeof payload.text !== "string" || !Number.isFinite(event?.created)) {
      fail("logs", "A textual Vercel build event is malformed.");
    }
    const text = payload.text.replace(/\u001b\[[0-9;]*m/g, "").trim();
    aggregateBytes += Buffer.byteLength(text);
    if (aggregateBytes > MAX_BUILD_LOG_BYTES) {
      fail("logs", "Normalized Vercel build logs exceeded the size limit.");
    }
    const serial = Number(payload.serial ?? index);
    if (!Number.isFinite(serial)) {
      fail("logs", "A Vercel build-event serial is malformed.");
    }
    logs.push({ index, created: event.created, serial, text });
  }
  if (logs.length === 0) {
    fail("logs_pending", "Vercel build events contain no textual records.");
  }
  logs.sort(
    (left, right) =>
      left.created - right.created || left.serial - right.serial || left.index - right.index
  );
  return logs.map((log, index) => ({ ...log, index }));
}

function parseBuildMarkers(logs, expectedLockHash) {
  const markers = [];
  for (const log of logs) {
    if (!log.text.startsWith("{")) {
      continue;
    }
    try {
      const value = JSON.parse(log.text);
      if (value?.contract === "f04.build-toolchain") {
        markers.push(value);
      }
    } catch {
      // Non-JSON log lines are expected.
    }
  }
  if (markers.length !== 3) {
    fail("logs_pending", "Build logs must contain exactly three toolchain records.");
  }
  const lifecycles = ["preinstall", "prebuild", "postbuild"];
  for (let index = 0; index < lifecycles.length; index += 1) {
    const marker = markers[index];
    if (
      marker.schema_version !== 1 ||
      marker.result !== "PASSED" ||
      marker.lifecycle !== lifecycles[index] ||
      marker.environment !== "vercel" ||
      marker.package_lock_sha256 !== expectedLockHash ||
      marker.npm !== "11.18.0" ||
      !/^24\.\d+\.\d+$/.test(marker.node) ||
      marker.next_version !== "16.2.10"
    ) {
      fail("logs", "A build toolchain marker does not match the exact contract.");
    }
  }
  return markers;
}

async function collectVercelBuildLogs(
  fetchImpl,
  token,
  deploymentId,
  teamId,
  runtime,
  expectedLockHash
) {
  let pending = null;
  for (let attempt = 1; attempt <= MAX_BUILD_LOG_ATTEMPTS; attempt += 1) {
    try {
      const events = await requestBuildEvents(fetchImpl, token, deploymentId, teamId);
      const logs = normalizeBuildLogs(events, deploymentId);
      const markers = parseBuildMarkers(logs, expectedLockHash);
      return { logs, markers, attempts: attempt };
    } catch (error) {
      if (!(error instanceof VercelResourceMeasurementError) || error.code !== "logs_pending") {
        throw error;
      }
      pending = error;
      if (attempt < MAX_BUILD_LOG_ATTEMPTS) {
        await runtime.sleep(BUILD_LOG_RETRY_MS);
      }
    }
  }
  fail("logs", `Vercel build logs did not become complete: ${pending?.message ?? "pending"}.`);
}

function parseSingle(logs, pattern, label, transform = (match) => Number(match[1])) {
  const matches = logs
    .map(({ text }) => text.match(pattern))
    .filter((match) => match !== null);
  if (matches.length !== 1) {
    fail("logs", `Build logs must contain exactly one ${label} record.`);
  }
  return transform(matches[0]);
}

function parseBuildMeasurements(logs, deployment, markers) {
  const machine = parseSingle(
    logs,
    /^Build machine configuration: (\d+) cores, ([0-9.]+) GB$/,
    "build machine",
    (match) => ({ cores: Number(match[1]), memoryMb: Math.round(Number(match[2]) * 1024) })
  );
  const browser = parseSingle(
    logs,
    /^Browser confidentiality check passed: (\d+) files, (\d+) bytes\.$/,
    "browser footprint",
    (match) => ({ files: Number(match[1]), bytes: Number(match[2]) })
  );
  const cacheRestored = logs.filter(({ text }) =>
    /^Restored build cache from previous deployment \([A-Za-z0-9]+\)$/.test(text)
  );
  if (cacheRestored.length > 1) {
    fail("logs", "Build logs contain ambiguous cache-restore records.");
  }
  const cacheUploadMb = parseSingle(
    logs,
    /Uploading build cache \[([0-9.]+) MB\]/,
    "cache upload size"
  );
  const createdAt = Date.parse(deployment.created_at);
  const readyAt = Date.parse(deployment.ready_at);
  if (!Number.isFinite(createdAt) || !Number.isFinite(readyAt) || readyAt < createdAt) {
    fail("measurement", "Deployment timing metadata is invalid.");
  }
  const finalMarker = markers.at(-1);
  if (!finalMarker) {
    fail("logs", "The final toolchain marker is missing.");
  }
  return {
    build: {
      duration_ms: Math.round(
        parseSingle(logs, /^Build Completed in \/vercel\/output \[([0-9.]+)s\]$/, "build duration") *
          1000
      ),
      deployment_elapsed_ms: readyAt - createdAt,
      clone_ms: Math.round(parseSingle(logs, /^Cloning completed: ([0-9.]+)s$/, "clone duration") * 1000),
      install_ms: Math.round(
        parseSingle(
          logs,
          /^added \d+ packages, and audited \d+ packages in ([0-9.]+)s$/,
          "install duration"
        ) * 1000
      ),
      compile_ms: Math.round(
        parseSingle(logs, /Compiled successfully in ([0-9.]+)s$/, "compile duration") * 1000
      ),
      typecheck_ms: Math.round(
        parseSingle(logs, /Finished TypeScript in ([0-9.]+)s \.\.\.$/, "TypeScript duration") * 1000
      ),
      static_generation_ms: Math.round(
        parseSingle(
          logs,
          /Generating static pages using \d+ worker \(\d+\/\d+\) in ([0-9.]+)ms$/,
          "static generation duration"
        )
      ),
      machine_cores: machine.cores,
      machine_memory_mb: machine.memoryMb,
      vercel_cli: parseSingle(
        logs,
        /^Vercel CLI ([0-9.]+)$/,
        "Vercel CLI version",
        (match) => match[1]
      )
    },
    artifact: browser,
    cache: {
      restored: cacheRestored.length === 1,
      created_ms: Math.round(
        parseSingle(logs, /^Created build cache: ([0-9.]+)s$/, "cache creation duration") * 1000
      ),
      uploaded_bytes: Math.round(cacheUploadMb * 1_000_000),
      upload_ms: Math.round(
        parseSingle(logs, /^Build cache uploaded: ([0-9.]+)s$/, "cache upload duration") * 1000
      ),
      causal_speedup_claimed: false
    },
    runtime: {
      node: finalMarker.node,
      npm: finalMarker.npm,
      next: finalMarker.next_version
    }
  };
}

async function readBoundedBody(response, maximumBytes, label) {
  const declared = Number(response.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > maximumBytes) {
    fail("http", `${label} exceeds the response-size limit.`);
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.byteLength > maximumBytes) {
    fail("http", `${label} exceeds the response-size limit.`);
  }
  return new TextDecoder().decode(bytes);
}

function isAuthenticationResponse(response, body) {
  const lower = body.toLowerCase();
  return (
    response.status >= 300 ||
    Boolean(response.headers.get("location")) ||
    lower.includes("vercel authentication") ||
    lower.includes("log in to vercel") ||
    lower.includes("deployment protection")
  );
}

async function timedProtectedRequest(fetchImpl, monotonicNow, url, bypassSecret) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);
  const started = monotonicNow();
  let response;
  let headersAt;
  let body;
  try {
    response = await fetchImpl(url, {
      redirect: "manual",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "cache-control": "no-cache",
        "x-vercel-protection-bypass": bypassSecret
      }
    });
    headersAt = monotonicNow();
    body = await readBoundedBody(response, MAX_PAGE_BYTES, "Protected measurement page");
  } catch (error) {
    if (error instanceof VercelResourceMeasurementError) {
      throw error;
    }
    fail("http", "Protected measurement request failed or timed out.");
  } finally {
    clearTimeout(timeout);
  }
  const ended = monotonicNow();
  if (isAuthenticationResponse(response, body)) {
    fail("http", "Protected measurement request returned authentication content.");
  }
  if (response.status !== 200 || !/text\/html/i.test(response.headers.get("content-type") ?? "")) {
    fail("http", "Protected measurement request did not return HTTP 200 HTML.");
  }
  verifyPageSemantics(body);
  const cache = (response.headers.get("x-vercel-cache") ?? "UNKNOWN").toUpperCase();
  const vercelId = response.headers.get("x-vercel-id") ?? "";
  const region = /^[a-z0-9]+/i.exec(vercelId)?.[0]?.toLowerCase() ?? "unknown";
  const sample = {
    ttfb_ms: Math.max(0, Math.round(headersAt - started)),
    total_ms: Math.max(0, Math.round(ended - started)),
    status: response.status,
    body_bytes: Buffer.byteLength(body),
    cache,
    edge_region: region
  };
  return { sample, body };
}

async function deployedAssetFootprint(fetchImpl, hostname, body, bypassSecret) {
  const pageUrl = `https://${hostname}/`;
  const assets = extractStaticAssets(body, pageUrl);
  if (assets.length > MAX_ASSET_COUNT) {
    fail("http", "Deployed asset count exceeds the bounded limit.");
  }
  let bytes = 0;
  for (const assetUrl of assets) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);
    let response;
    let assetBody;
    try {
      response = await fetchImpl(assetUrl, {
        redirect: "manual",
        cache: "no-store",
        signal: controller.signal,
        headers: { "x-vercel-protection-bypass": bypassSecret }
      });
      assetBody = await readBoundedBody(response, MAX_ASSET_BYTES, "Protected measurement asset");
    } catch (error) {
      if (error instanceof VercelResourceMeasurementError) {
        throw error;
      }
      fail("http", "Protected measurement asset request failed or timed out.");
    } finally {
      clearTimeout(timeout);
    }
    if (response.status !== 200 || !/(javascript|css|text\/plain)/i.test(response.headers.get("content-type") ?? "")) {
      fail("http", "Protected measurement asset response is invalid.");
    }
    bytes += Buffer.byteLength(assetBody);
    if (bytes > MAX_AGGREGATE_ASSET_BYTES) {
      fail("http", "Deployed asset footprint exceeds the bounded limit.");
    }
  }
  return { count: assets.length, bytes };
}

function percentile(values, fraction) {
  const ordered = [...values].sort((left, right) => left - right);
  const index = Math.max(0, Math.ceil(ordered.length * fraction) - 1);
  return ordered[index];
}

async function observeTeamPlan(fetchImpl, token, teamId) {
  let response;
  try {
    response = await fetchImpl(`https://api.vercel.com/v2/teams/${encodeURIComponent(teamId)}`, {
      redirect: "manual",
      headers: { authorization: `Bearer ${token}` }
    });
  } catch {
    fail("cost", "Vercel team-plan request failed.");
  }
  if (!response.ok) {
    fail("cost", `Vercel team-plan request returned HTTP ${response.status}.`);
  }
  const text = await readBoundedBody(response, MAX_TEAM_RESPONSE_BYTES, "Vercel team metadata");
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    fail("cost", "Vercel team metadata is not valid JSON.");
  }
  const plan = payload?.billing?.plan ?? payload?.plan ?? "not_exposed";
  return typeof plan === "string" && /^[a-z0-9_-]+$/i.test(plan) ? plan.toLowerCase() : "not_exposed";
}

function assertEvidenceSafe(evidence, secrets = []) {
  const serialized = JSON.stringify(evidence);
  const forbiddenPatterns = [
    /https?:\/\//i,
    /authorization/i,
    /cookie/i,
    /bearer\s/i,
    /x-vercel-protection/i,
    /"[^\"]*(?:token|secret|password|credential)[^\"]*"\s*:/i
  ];
  if (forbiddenPatterns.some((pattern) => pattern.test(serialized))) {
    fail("confidentiality", "Sanitized resource evidence contains forbidden material.");
  }
  for (const secret of secrets) {
    if (typeof secret === "string" && secret.length > 0 && serialized.includes(secret)) {
      fail("confidentiality", "Sanitized resource evidence contains a credential value.");
    }
  }
}

export function validateResourceMeasurementEvidence(evidence, expected = {}) {
  assertExactKeys(evidence, EVIDENCE_KEYS, "Resource measurement evidence");
  assertExactKeys(evidence.deployment, ["deployment_id", "created_at", "ready_at", "regions"], "Deployment measurements");
  assertExactKeys(
    evidence.build,
    [
      "duration_ms",
      "deployment_elapsed_ms",
      "clone_ms",
      "install_ms",
      "compile_ms",
      "typecheck_ms",
      "static_generation_ms",
      "machine_cores",
      "machine_memory_mb",
      "vercel_cli"
    ],
    "Build measurements"
  );
  assertExactKeys(
    evidence.artifact_footprint,
    [
      "browser_build_files",
      "browser_build_bytes",
      "deployed_html_bytes",
      "deployed_asset_count",
      "deployed_asset_bytes",
      "deployed_total_bytes"
    ],
    "Artifact footprint"
  );
  assertExactKeys(
    evidence.cache,
    ["restored", "created_ms", "uploaded_bytes", "upload_ms", "causal_speedup_claimed"],
    "Cache observation"
  );
  assertExactKeys(
    evidence.latency,
    [
      "classification",
      "quiescence_ms",
      "cold",
      "warm_samples",
      "warm_ttfb_median_ms",
      "warm_total_median_ms",
      "warm_total_p95_ms",
      "infrastructure_cold_start_claimed"
    ],
    "Latency observation"
  );
  assertExactKeys(evidence.latency.cold, ["ttfb_ms", "total_ms", "status", "body_bytes", "cache", "edge_region"], "Cold sample");
  if (!Array.isArray(evidence.latency.warm_samples) || evidence.latency.warm_samples.length !== DEFAULT_WARM_SAMPLE_COUNT) {
    fail("evidence", "Latency evidence must contain five warm samples.");
  }
  for (const sample of evidence.latency.warm_samples) {
    assertExactKeys(sample, ["ttfb_ms", "total_ms", "status", "body_bytes", "cache", "edge_region"], "Warm sample");
  }
  assertExactKeys(evidence.runtime, ["node", "npm", "next"], "Runtime observation");
  assertExactKeys(
    evidence.cost_observation,
    [
      "team_plan",
      "preview_deployments_observed",
      "measurement_http_requests",
      "build_duration_ms",
      "cache_upload_bytes",
      "dollar_estimate_provided",
      "bounded"
    ],
    "Cost observation"
  );
  assertExactKeys(
    evidence.assertions,
    [
      "exact_deployment_bound",
      "build_measurements_recorded",
      "artifact_footprint_recorded",
      "cache_impact_recorded",
      "latency_samples_bounded",
      "runtime_versions_recorded",
      "cost_observation_bounded",
      "confidential_material_absent"
    ],
    "Resource assertions"
  );

  const expectedSha = expected.expectedSha ?? evidence.expected_git_sha;
  const expectedDeploymentId = expected.deploymentId ?? evidence.deployment?.deployment_id;
  if (
    evidence.schema_version !== 1 ||
    evidence.phase !== "F04" ||
    evidence.blocker_id !== "f04.resource_measurements" ||
    evidence.result !== "PASSED" ||
    !Number.isFinite(Date.parse(evidence.verified_at)) ||
    evidence.expected_git_sha !== expectedSha ||
    !/^[0-9a-f]{40}$/.test(evidence.expected_git_sha) ||
    evidence.deployment.deployment_id !== expectedDeploymentId ||
    !/^dpl_[A-Za-z0-9]+$/.test(evidence.deployment.deployment_id) ||
    !Number.isFinite(Date.parse(evidence.deployment.created_at)) ||
    !Number.isFinite(Date.parse(evidence.deployment.ready_at)) ||
    !Array.isArray(evidence.deployment.regions) ||
    evidence.deployment.regions.length === 0 ||
    evidence.latency.classification !== "first-after-bounded-quiescence" ||
    evidence.latency.quiescence_ms !== DEFAULT_QUIESCENCE_MS ||
    evidence.latency.infrastructure_cold_start_claimed !== false ||
    evidence.cache.causal_speedup_claimed !== false ||
    evidence.cost_observation.preview_deployments_observed !== 1 ||
    evidence.cost_observation.dollar_estimate_provided !== false ||
    evidence.cost_observation.bounded !== true ||
    !Object.values(evidence.assertions).every((value) => value === true) ||
    !/^24\.\d+\.\d+$/.test(evidence.runtime.node) ||
    evidence.runtime.npm !== "11.18.0" ||
    evidence.runtime.next !== "16.2.10"
  ) {
    fail("evidence", "Resource evidence does not prove the required contract.");
  }

  for (const [label, value, max] of [
    ["build duration", evidence.build.duration_ms, 600_000],
    ["deployment elapsed", evidence.build.deployment_elapsed_ms, 900_000],
    ["clone duration", evidence.build.clone_ms, 120_000],
    ["install duration", evidence.build.install_ms, 300_000],
    ["compile duration", evidence.build.compile_ms, 300_000],
    ["typecheck duration", evidence.build.typecheck_ms, 300_000],
    ["static generation duration", evidence.build.static_generation_ms, 300_000],
    ["cache creation", evidence.cache.created_ms, 300_000],
    ["cache upload", evidence.cache.upload_ms, 300_000],
    ["cache upload bytes", evidence.cache.uploaded_bytes, 2_000_000_000],
    ["browser build bytes", evidence.artifact_footprint.browser_build_bytes, 50_000_000],
    ["deployed total bytes", evidence.artifact_footprint.deployed_total_bytes, 5_000_000]
  ]) {
    requireFinite(value, label, 1, max);
  }
  if (
    !Number.isInteger(evidence.build.machine_cores) ||
    evidence.build.machine_cores <= 0 ||
    !Number.isInteger(evidence.build.machine_memory_mb) ||
    evidence.build.machine_memory_mb <= 0 ||
    !Number.isInteger(evidence.artifact_footprint.browser_build_files) ||
    evidence.artifact_footprint.browser_build_files <= 0 ||
    !Number.isInteger(evidence.artifact_footprint.deployed_asset_count) ||
    evidence.artifact_footprint.deployed_asset_count <= 0 ||
    evidence.artifact_footprint.deployed_total_bytes !==
      evidence.artifact_footprint.deployed_html_bytes + evidence.artifact_footprint.deployed_asset_bytes
  ) {
    fail("evidence", "Resource count or footprint evidence is invalid.");
  }
  const samples = [evidence.latency.cold, ...evidence.latency.warm_samples];
  for (const sample of samples) {
    requireFinite(sample.ttfb_ms, "latency TTFB", 0, HTTP_TIMEOUT_MS);
    requireFinite(sample.total_ms, "latency total", 0, HTTP_TIMEOUT_MS);
    if (
      sample.total_ms < sample.ttfb_ms ||
      sample.status !== 200 ||
      !Number.isInteger(sample.body_bytes) ||
      sample.body_bytes <= 0 ||
      !/^[A-Z_-]+$/.test(sample.cache) ||
      !/^(?:[a-z0-9]+|unknown)$/.test(sample.edge_region)
    ) {
      fail("evidence", "A latency sample is invalid.");
    }
  }
  assertEvidenceSafe(evidence);
  return true;
}

export async function verifyVercelResourceMeasurements(input, dependencies = {}) {
  if (typeof input.packageLockSha256 !== "string" || !/^[0-9a-f]{64}$/.test(input.packageLockSha256)) {
    fail("configuration", "The package-lock SHA-256 is required.");
  }
  if (typeof input.bypassSecret !== "string" || !/^[A-Za-z0-9]{32}$/.test(input.bypassSecret)) {
    fail("configuration", "The Vercel automation bypass secret is invalid.");
  }
  const sleep = dependencies.sleep ?? ((milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)));
  const monotonicNow = dependencies.monotonicNow ?? (() => performance.now());
  const fetchImpl = dependencies.fetchImpl ?? globalThis.fetch;
  const discover = dependencies.discoverDeployment ?? discoverAndValidateExactDeployment;
  const collect = dependencies.collectBuildLogs ?? collectVercelBuildLogs;
  if (typeof fetchImpl !== "function" || typeof sleep !== "function" || typeof monotonicNow !== "function") {
    fail("configuration", "Measurement runtime dependencies are invalid.");
  }

  const exactDeployment = await discover(
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
  const buildLogs = await collect(
    fetchImpl,
    input.vercelApiToken,
    exactDeployment.deployment.deployment_id,
    input.teamId,
    exactDeployment.runtime,
    input.packageLockSha256
  );
  const parsed = parseBuildMeasurements(
    buildLogs.logs,
    exactDeployment.deployment,
    buildLogs.markers
  );
  const teamPlan = await observeTeamPlan(fetchImpl, input.vercelApiToken, input.teamId);

  const quiescenceMs = input.quiescenceMs ?? DEFAULT_QUIESCENCE_MS;
  const warmCount = input.warmSampleCount ?? DEFAULT_WARM_SAMPLE_COUNT;
  const warmIntervalMs = input.warmIntervalMs ?? DEFAULT_WARM_INTERVAL_MS;
  if (
    quiescenceMs !== DEFAULT_QUIESCENCE_MS ||
    warmCount !== DEFAULT_WARM_SAMPLE_COUNT ||
    !Number.isFinite(warmIntervalMs) ||
    warmIntervalMs < 0 ||
    warmIntervalMs > 5_000
  ) {
    fail("configuration", "The production measurement policy must remain fixed and bounded.");
  }

  await sleep(quiescenceMs);
  const probeUrl = `https://${exactDeployment.deployment.immutable_hostname}/?f04-resource-probe=${input.expectedSha}`;
  const coldResult = await timedProtectedRequest(fetchImpl, monotonicNow, probeUrl, input.bypassSecret);
  const warmSamples = [];
  for (let index = 0; index < warmCount; index += 1) {
    if (index > 0 && warmIntervalMs > 0) {
      await sleep(warmIntervalMs);
    }
    const result = await timedProtectedRequest(fetchImpl, monotonicNow, probeUrl, input.bypassSecret);
    warmSamples.push(result.sample);
  }
  const deployedAssets = await deployedAssetFootprint(
    fetchImpl,
    exactDeployment.deployment.immutable_hostname,
    coldResult.body,
    input.bypassSecret
  );
  const warmTtfb = warmSamples.map(({ ttfb_ms }) => ttfb_ms);
  const warmTotal = warmSamples.map(({ total_ms }) => total_ms);
  const measurementRequests = 1 + warmSamples.length + deployedAssets.count;

  const evidence = {
    schema_version: 1,
    phase: "F04",
    blocker_id: "f04.resource_measurements",
    result: "PASSED",
    verified_at: new Date(exactDeployment.runtime.now()).toISOString(),
    expected_git_sha: input.expectedSha,
    deployment: {
      deployment_id: exactDeployment.deployment.deployment_id,
      created_at: exactDeployment.deployment.created_at,
      ready_at: exactDeployment.deployment.ready_at,
      regions: exactDeployment.deployment.regions
    },
    build: parsed.build,
    artifact_footprint: {
      browser_build_files: parsed.artifact.files,
      browser_build_bytes: parsed.artifact.bytes,
      deployed_html_bytes: coldResult.sample.body_bytes,
      deployed_asset_count: deployedAssets.count,
      deployed_asset_bytes: deployedAssets.bytes,
      deployed_total_bytes: coldResult.sample.body_bytes + deployedAssets.bytes
    },
    cache: parsed.cache,
    latency: {
      classification: "first-after-bounded-quiescence",
      quiescence_ms: quiescenceMs,
      cold: coldResult.sample,
      warm_samples: warmSamples,
      warm_ttfb_median_ms: percentile(warmTtfb, 0.5),
      warm_total_median_ms: percentile(warmTotal, 0.5),
      warm_total_p95_ms: percentile(warmTotal, 0.95),
      infrastructure_cold_start_claimed: false
    },
    runtime: parsed.runtime,
    cost_observation: {
      team_plan: teamPlan,
      preview_deployments_observed: 1,
      measurement_http_requests: measurementRequests,
      build_duration_ms: parsed.build.duration_ms,
      cache_upload_bytes: parsed.cache.uploaded_bytes,
      dollar_estimate_provided: false,
      bounded: true
    },
    assertions: {
      exact_deployment_bound: true,
      build_measurements_recorded: true,
      artifact_footprint_recorded: true,
      cache_impact_recorded: true,
      latency_samples_bounded: true,
      runtime_versions_recorded: true,
      cost_observation_bounded: true,
      confidential_material_absent: true
    }
  };
  validateResourceMeasurementEvidence(evidence, {
    expectedSha: input.expectedSha,
    deploymentId: exactDeployment.deployment.deployment_id
  });
  assertEvidenceSafe(evidence, [input.githubToken, input.vercelApiToken, input.bypassSecret]);
  return evidence;
}

export function packageLockSha256(text) {
  if (typeof text !== "string") {
    fail("configuration", "Package-lock content is required.");
  }
  return createHash("sha256").update(text).digest("hex");
}
