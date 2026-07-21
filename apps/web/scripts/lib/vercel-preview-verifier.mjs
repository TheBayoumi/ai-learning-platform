import { createHash } from "node:crypto";

import {
  BrowserConfidentialityError,
  scanBrowserText
} from "./browser-confidentiality.mjs";

export const EXIT_CODES = Object.freeze({
  configuration: 2,
  discovery: 3,
  metadata_mismatch: 4,
  deployment_not_ready: 5,
  authentication_response: 6,
  http_failure: 7,
  semantic_mismatch: 8,
  confidentiality_failure: 9,
  evidence_write_failure: 10
});

const DEFAULT_POLLING = Object.freeze({
  maximum_duration_ms: 300_000,
  initial_interval_ms: 5_000,
  maximum_interval_ms: 15_000,
  backoff_multiplier: 1.5
});
const MAX_PAGE_BYTES = 128 * 1024;
const MAX_ASSET_BYTES = 512 * 1024;
const MAX_AGGREGATE_ASSET_BYTES = 2 * 1024 * 1024;
const MAX_ASSET_COUNT = 64;
const HTTP_TIMEOUT_MS = 30_000;
const EXPECTED_VISIBLE_COPY = Object.freeze([
  "AI Career Learning Platform",
  "Technical foundation",
  "API integration",
  "Local API unavailable",
  "Foundation boundary"
]);
const ALLOWED_EVIDENCE_KEYS = Object.freeze([
  "schema_version",
  "phase",
  "blocker_id",
  "result",
  "verified_at",
  "expected",
  "discovery",
  "deployment",
  "http",
  "semantics",
  "confidentiality"
]);

export class VerifierError extends Error {
  constructor(kind, message, details = {}) {
    super(message);
    this.name = "VerifierError";
    this.kind = kind;
    this.exitCode = EXIT_CODES[kind] ?? 1;
    this.details = Object.freeze({ ...details });
  }
}

function fail(kind, message, details = {}) {
  throw new VerifierError(kind, message, details);
}

function requireString(value, label) {
  if (typeof value !== "string" || value.length === 0) {
    fail("configuration", `${label} is required.`);
  }
  return value;
}

function assertExactKeys(value, allowed, label, kind = "metadata_mismatch") {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail(kind, `${label} must be an object.`);
  }
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length > 0) {
    fail(kind, `${label} contains unknown fields.`, { fields: unknown.sort() });
  }
}

function validateInputs(input) {
  const expectedSha = requireString(input.expectedSha, "expected SHA");
  if (!/^[0-9a-f]{40}$/.test(expectedSha)) {
    fail("configuration", "Expected SHA must be a full lowercase Git SHA.");
  }
  const repository = requireString(input.repository, "repository");
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) {
    fail("configuration", "Repository must use the owner/name form.");
  }
  const branch = requireString(input.branch, "branch");
  const projectId = requireString(input.projectId, "Vercel project ID");
  const teamId = requireString(input.teamId, "Vercel team ID");
  requireString(input.githubToken, "GitHub token");
  requireString(input.vercelApiToken, "Vercel API token");
  requireString(input.bypassSecret, "Vercel automation bypass secret");
  if (!/^[A-Za-z0-9]{32}$/.test(input.bypassSecret)) {
    fail("configuration", "Vercel automation bypass secret has an invalid shape.");
  }
  return { expectedSha, repository, branch, projectId, teamId };
}

function safeJsonParse(text, kind, label) {
  try {
    return JSON.parse(text);
  } catch {
    fail(kind, `${label} returned invalid JSON.`);
  }
}

async function readBoundedResponse(response, maximumBytes, label) {
  const declaredLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) {
    fail("http_failure", `${label} exceeds the response-size limit.`);
  }

  if (!response.body || typeof response.body.getReader !== "function") {
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.byteLength > maximumBytes) {
      fail("http_failure", `${label} exceeds the response-size limit.`);
    }
    return new TextDecoder().decode(bytes);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let total = 0;
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    total += value.byteLength;
    if (total > maximumBytes) {
      await reader.cancel();
      fail("http_failure", `${label} exceeds the response-size limit.`);
    }
    result += decoder.decode(value, { stream: true });
  }
  return result + decoder.decode();
}

async function requestJson(fetchImpl, url, headers, label) {
  let response;
  try {
    response = await fetchImpl(url, { headers, redirect: "manual" });
  } catch {
    fail("discovery", `${label} request failed.`);
  }
  if (!response.ok) {
    fail("discovery", `${label} returned HTTP ${response.status}.`, {
      status: response.status
    });
  }
  const text = await readBoundedResponse(response, MAX_PAGE_BYTES, label);
  return safeJsonParse(text, "discovery", label);
}

function selectUniqueLatest(records, timestampFields, label) {
  if (!Array.isArray(records) || records.length === 0) {
    fail("discovery", `${label} is missing.`);
  }
  const withTime = records.map((record) => {
    const raw = timestampFields.map((field) => record[field]).find(Boolean);
    const time = Date.parse(raw ?? "");
    if (!Number.isFinite(time)) {
      fail("discovery", `${label} contains an invalid timestamp.`);
    }
    return { record, time };
  });
  const latestTime = Math.max(...withTime.map(({ time }) => time));
  const latest = withTime.filter(({ time }) => time === latestTime);
  if (latest.length !== 1) {
    fail("discovery", `${label} latest result is ambiguous.`);
  }
  return latest[0].record;
}

function parseInspectorDeploymentId(targetUrl) {
  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    fail("discovery", "Vercel status target URL is invalid.");
  }
  if (
    parsed.protocol !== "https:" ||
    parsed.hostname !== "vercel.com" ||
    parsed.search ||
    parsed.hash
  ) {
    fail("discovery", "Vercel status target URL is not a canonical inspector URL.");
  }
  const segments = parsed.pathname.split("/").filter(Boolean);
  if (segments.length !== 3 || !/^(?:dpl_)?[A-Za-z0-9]+$/.test(segments[2])) {
    fail("discovery", "Vercel status target URL does not contain a canonical deployment ID.");
  }
  return segments[2].startsWith("dpl_") ? segments[2] : `dpl_${segments[2]}`;
}

function normalizeHostname(value, label) {
  let parsed;
  try {
    parsed = new URL(value.startsWith("http") ? value : `https://${value}`);
  } catch {
    fail("discovery", `${label} is invalid.`);
  }
  if (parsed.protocol !== "https:" || parsed.pathname !== "/" || parsed.search || parsed.hash) {
    fail("discovery", `${label} must be a bare HTTPS hostname.`);
  }
  return parsed.hostname.toLowerCase();
}

function isAuthenticationResponse(response, body) {
  const location = response.headers.get("location") ?? "";
  const content = body.toLowerCase();
  return (
    (response.status >= 300 && response.status < 400) ||
    location.length > 0 ||
    content.includes("vercel authentication") ||
    content.includes("vercel sso") ||
    content.includes("log in to vercel") ||
    content.includes("deployment protection")
  );
}

function parseAttributes(tag) {
  const attributes = {};
  const pattern = /([:\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
  for (const match of tag.matchAll(pattern)) {
    attributes[match[1].toLowerCase()] = match[2] ?? match[3] ?? match[4] ?? "";
  }
  return attributes;
}

function decodeHtml(value) {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)));
}

function visibleText(html) {
  return decodeHtml(
    html
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
  )
    .replace(/\s+/g, " ")
    .trim();
}

function textForId(html, id) {
  const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = html.match(
    new RegExp(`<([a-z0-9-]+)\\b[^>]*\\bid=["']${escaped}["'][^>]*>([\\s\\S]*?)<\\/\\1>`, "i")
  );
  return match ? visibleText(match[2]) : null;
}

export function verifyPageSemantics(html) {
  const text = visibleText(html);
  for (const expected of EXPECTED_VISIBLE_COPY) {
    if (!text.includes(expected)) {
      fail("semantic_mismatch", "Rendered page is missing required accessible copy.", {
        expected
      });
    }
  }

  const stateTags = [...html.matchAll(/<[^>]+\bdata-api-state=(?:"([^"]*)"|'([^']*)')[^>]*>/gi)];
  if (stateTags.length !== 1 || (stateTags[0][1] ?? stateTags[0][2]) !== "unavailable") {
    fail("semantic_mismatch", "Rendered page does not expose exactly one unavailable API state.");
  }
  if (/data-api-state=(?:"|')(?:available|invalid-response)(?:"|')/i.test(html)) {
    fail("semantic_mismatch", "Rendered page exposes a contradictory API state.");
  }

  const statusTags = [...html.matchAll(/<[^>]+\brole=(?:"status"|'status')[^>]*>/gi)];
  if (statusTags.length !== 1) {
    fail("semantic_mismatch", "Rendered page must expose exactly one status region.");
  }
  const attributes = parseAttributes(statusTags[0][0]);
  if (attributes["aria-atomic"] !== "true") {
    fail("semantic_mismatch", "Status region must be atomic.");
  }
  const labelledBy = attributes["aria-labelledby"];
  const describedBy = attributes["aria-describedby"];
  if (!labelledBy || !describedBy) {
    fail("semantic_mismatch", "Status region must reference a label and description.");
  }
  const label = textForId(html, labelledBy);
  const description = textForId(html, describedBy);
  if (label !== "Local API unavailable" || !description) {
    fail("semantic_mismatch", "Status region references invalid accessible content.");
  }

  return Object.freeze({
    api_state: "unavailable",
    status_role_count: 1,
    status_label: label,
    status_description_present: true,
    required_copy: EXPECTED_VISIBLE_COPY
  });
}

export function extractStaticAssets(html, pageUrl) {
  const urls = [];
  for (const match of html.matchAll(/<(script|link)\b[^>]*>/gi)) {
    const attributes = parseAttributes(match[0]);
    const candidate =
      match[1].toLowerCase() === "script"
        ? attributes.src
        : attributes.rel?.toLowerCase() === "stylesheet"
          ? attributes.href
          : undefined;
    if (!candidate) {
      continue;
    }
    const resolved = new URL(candidate, pageUrl);
    if (resolved.origin !== new URL(pageUrl).origin) {
      fail("confidentiality_failure", "Rendered page references a cross-origin executable asset.");
    }
    if (!resolved.pathname.startsWith("/_next/static/")) {
      fail("confidentiality_failure", "Rendered page references an unexpected executable asset path.");
    }
    urls.push(resolved.href);
  }
  if (new Set(urls).size !== urls.length) {
    fail("confidentiality_failure", "Rendered page contains duplicate static asset references.");
  }
  if (urls.length === 0 || urls.length > MAX_ASSET_COUNT) {
    fail("confidentiality_failure", "Rendered page has an invalid static asset count.");
  }
  return urls.sort();
}

async function fetchProtectedText(
  fetchImpl,
  url,
  bypassSecret,
  maximumBytes,
  label,
  timeoutMs = HTTP_TIMEOUT_MS
) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  let body = "";
  try {
    response = await fetchImpl(url, {
      redirect: "manual",
      signal: controller.signal,
      headers: {
        "x-vercel-protection-bypass": bypassSecret
      }
    });
    body = await readBoundedResponse(response, maximumBytes, label);
  } catch (error) {
    if (error instanceof VerifierError) {
      throw error;
    }
    fail("http_failure", `${label} request failed or timed out.`);
  } finally {
    clearTimeout(timeout);
  }
  if (isAuthenticationResponse(response, body)) {
    fail("authentication_response", `${label} returned authentication content.`);
  }
  if (response.status !== 200) {
    fail("http_failure", `${label} returned HTTP ${response.status}.`, {
      status: response.status
    });
  }
  return { response, body };
}

async function discoverExactDeployment(input, dependencies, polling) {
  const { fetchImpl, sleep, now } = dependencies;
  const githubHeaders = {
    accept: "application/vnd.github+json",
    authorization: `Bearer ${input.githubToken}`,
    "x-github-api-version": "2022-11-28"
  };
  const started = now();
  let attempts = 0;
  let interval = polling.initial_interval_ms;

  while (true) {
    attempts += 1;
    const statusPayload = await requestJson(
      fetchImpl,
      `https://api.github.com/repos/${input.repository}/commits/${input.expectedSha}/status`,
      githubHeaders,
      "GitHub combined status"
    );
    if (statusPayload.sha !== input.expectedSha) {
      fail("discovery", "GitHub combined status belongs to another SHA.");
    }
    const vercelStatuses = (statusPayload.statuses ?? []).filter(
      (status) => status.context === "Vercel"
    );
    const latestVercelStatus =
      vercelStatuses.length > 0
        ? selectUniqueLatest(
            vercelStatuses,
            ["updated_at", "created_at"],
            "Vercel commit status"
          )
        : null;
    if (latestVercelStatus && ["failure", "error"].includes(latestVercelStatus.state)) {
      fail("discovery", "Vercel commit status is terminally unsuccessful.", {
        state: latestVercelStatus.state
      });
    }

    if (latestVercelStatus) {
      const deploymentId = parseInspectorDeploymentId(latestVercelStatus.target_url);
      const deployments = await requestJson(
        fetchImpl,
        `https://api.github.com/repos/${input.repository}/deployments?sha=${input.expectedSha}&environment=Preview`,
        githubHeaders,
        "GitHub deployment discovery"
      );
      const candidates = (Array.isArray(deployments) ? deployments : []).filter(
        (deployment) =>
          deployment.sha === input.expectedSha &&
          deployment.environment === "Preview" &&
          deployment.production_environment === false &&
          deployment.creator?.login === "vercel[bot]"
      );
      if (candidates.length > 1) {
        fail("discovery", "Exact SHA has ambiguous Vercel Preview deployments.");
      }

      if (latestVercelStatus.state === "success" && candidates.length === 1) {
      const deployment = candidates[0];
      const statuses = await requestJson(
        fetchImpl,
        `https://api.github.com/repos/${input.repository}/deployments/${deployment.id}/statuses`,
        githubHeaders,
        "GitHub deployment status"
      );
      if (!Array.isArray(statuses)) {
        fail("discovery", "GitHub deployment status response is invalid.");
      }
      const latestDeploymentStatus =
        statuses.length === 0
          ? null
          : selectUniqueLatest(
              statuses,
              ["updated_at", "created_at"],
              "GitHub deployment status"
            );
      if (
        latestDeploymentStatus &&
        ["failure", "error", "inactive"].includes(latestDeploymentStatus.state)
      ) {
        fail("discovery", "GitHub deployment status is terminally unsuccessful.", {
          state: latestDeploymentStatus.state
        });
      }
      if (latestDeploymentStatus?.state === "success") {
        const hostname = normalizeHostname(
          latestDeploymentStatus.environment_url,
          "GitHub immutable deployment URL"
        );
        return {
          deploymentId,
          hostname,
          githubDeploymentId: deployment.id,
          githubDeploymentStatusId: latestDeploymentStatus.id,
          vercelStatusTargetUrl: latestVercelStatus.target_url,
          attempts,
          startedAt: new Date(started).toISOString(),
          endedAt: new Date(now()).toISOString(),
          elapsedMs: now() - started,
          finalStatusContext: latestVercelStatus.context,
          finalStatusState: latestVercelStatus.state,
          finalStatusTimestamp:
            latestVercelStatus.updated_at ?? latestVercelStatus.created_at,
          polling
        };
      }
      }
    }

    const elapsed = now() - started;
    if (elapsed >= polling.maximum_duration_ms) {
      fail("discovery", "Exact-SHA Vercel discovery timed out.", { attempts, elapsed_ms: elapsed });
    }
    await sleep(Math.min(interval, polling.maximum_duration_ms - elapsed));
    interval = Math.min(
      Math.ceil(interval * polling.backoff_multiplier),
      polling.maximum_interval_ms
    );
  }
}

async function fetchAndValidateDeployment(input, discovery, fetchImpl) {
  const deployment = await requestJson(
    fetchImpl,
    `https://api.vercel.com/v13/deployments/${discovery.deploymentId}?teamId=${encodeURIComponent(input.teamId)}`,
    { authorization: `Bearer ${input.vercelApiToken}` },
    "Vercel deployment metadata"
  );
  const projectId = deployment.projectId ?? deployment.project?.id;
  const gitSha = deployment.gitSource?.sha ?? deployment.meta?.githubCommitSha;
  const gitBranch = deployment.gitSource?.ref ?? deployment.meta?.githubCommitRef;
  const repository = `${deployment.meta?.githubCommitOrg}/${deployment.meta?.githubCommitRepo}`;

  if (deployment.id !== discovery.deploymentId) {
    fail("metadata_mismatch", "Vercel metadata deployment ID does not match discovery.");
  }
  if (projectId !== input.projectId) {
    fail("metadata_mismatch", "Vercel deployment belongs to another project.");
  }
  if (deployment.readyState !== "READY") {
    fail("deployment_not_ready", "Vercel deployment is not READY.", {
      state: deployment.readyState ?? null
    });
  }
  if (deployment.target !== null && deployment.target !== undefined && deployment.target !== "preview") {
    fail("metadata_mismatch", "Vercel deployment is not a preview target.");
  }
  if (deployment.source !== "git" || deployment.gitSource?.type !== "github") {
    fail("metadata_mismatch", "Vercel deployment is not tied to GitHub source metadata.");
  }
  if (gitSha !== input.expectedSha || deployment.meta?.githubCommitSha !== input.expectedSha) {
    fail("metadata_mismatch", "Vercel deployment Git SHA differs from the expected SHA.");
  }
  if (gitBranch !== input.branch || deployment.meta?.githubCommitRef !== input.branch) {
    fail("metadata_mismatch", "Vercel deployment branch differs from the expected branch.");
  }
  if (repository !== input.repository) {
    fail("metadata_mismatch", "Vercel deployment repository differs from the expected repository.");
  }
  if (
    !Number.isFinite(deployment.createdAt) ||
    !Number.isFinite(deployment.ready) ||
    deployment.ready < deployment.createdAt ||
    !Array.isArray(deployment.regions) ||
    deployment.regions.length === 0
  ) {
    fail("metadata_mismatch", "Vercel deployment timing or region metadata is incomplete.");
  }
  const metadataHostname = normalizeHostname(deployment.url, "Vercel immutable deployment URL");
  if (metadataHostname !== discovery.hostname) {
    fail("metadata_mismatch", "GitHub and Vercel immutable deployment URLs differ.");
  }
  if (
    metadataHostname.includes("-git-") ||
    metadataHostname === "f04-reversion-proof-web.vercel.app"
  ) {
    fail("metadata_mismatch", "Discovered hostname is an alias instead of an immutable deployment URL.");
  }

  return {
    deployment_id: deployment.id,
    immutable_hostname: metadataHostname,
    project_id: projectId,
    git_sha: gitSha,
    git_branch: gitBranch,
    ready_state: deployment.readyState,
    target: deployment.target ?? null,
    source: deployment.source,
    git_source_type: deployment.gitSource.type,
    created_at: new Date(deployment.createdAt).toISOString(),
    ready_at: new Date(deployment.ready).toISOString(),
    regions: [...deployment.regions].sort()
  };
}

async function inspectProtectedPage(input, deployment, fetchImpl) {
  const pageUrl = `https://${deployment.immutable_hostname}/`;
  const { response, body } = await fetchProtectedText(
    fetchImpl,
    pageUrl,
    input.bypassSecret,
    MAX_PAGE_BYTES,
    "Protected preview page",
    input.httpTimeoutMs
  );
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("text/html")) {
    fail("http_failure", "Protected preview page did not return HTML.");
  }

  const semantics = verifyPageSemantics(body);
  try {
    scanBrowserText(body, {
      sourceLabel: "deployed HTML",
      secretValues: [input.bypassSecret, input.vercelApiToken, input.githubToken]
    });
  } catch (error) {
    if (error instanceof BrowserConfidentialityError) {
      fail("confidentiality_failure", "Deployed HTML failed confidentiality checks.", {
        issue_codes: error.issues.map(({ code }) => code)
      });
    }
    throw error;
  }

  const assetUrls = extractStaticAssets(body, pageUrl);
  const assets = [];
  let aggregateBytes = 0;
  for (const assetUrl of assetUrls) {
    const asset = await fetchProtectedText(
      fetchImpl,
      assetUrl,
      input.bypassSecret,
      MAX_ASSET_BYTES,
      "Protected preview static asset",
      input.httpTimeoutMs
    );
    const assetType = asset.response.headers.get("content-type") ?? "";
    if (!/(javascript|css|text\/plain)/i.test(assetType)) {
      fail("confidentiality_failure", "Static asset has an unexpected content type.");
    }
    aggregateBytes += Buffer.byteLength(asset.body);
    if (aggregateBytes > MAX_AGGREGATE_ASSET_BYTES) {
      fail("confidentiality_failure", "Static assets exceed the aggregate-size limit.");
    }
    try {
      scanBrowserText(asset.body, {
        sourceLabel: new URL(assetUrl).pathname,
        secretValues: [input.bypassSecret, input.vercelApiToken, input.githubToken]
      });
    } catch (error) {
      if (error instanceof BrowserConfidentialityError) {
        fail("confidentiality_failure", "A deployed static asset failed confidentiality checks.", {
          issue_codes: error.issues.map(({ code }) => code)
        });
      }
      throw error;
    }
    assets.push({
      content_type: assetType.split(";")[0],
      bytes: Buffer.byteLength(asset.body),
      sha256: createHash("sha256").update(asset.body).digest("hex")
    });
  }

  return {
    http: {
      url: pageUrl,
      status: response.status,
      redirect_chain: [response.status],
      authentication_response: false,
      content_type: contentType,
      cache_control: response.headers.get("cache-control"),
      body_bytes: Buffer.byteLength(body),
      body_sha256: createHash("sha256").update(body).digest("hex")
    },
    semantics,
    confidentiality: {
      forbidden_markers_absent: true,
      loopback_absent: true,
      health_path_absent: true,
      trace_context_absent: true,
      html_scanned_bytes: Buffer.byteLength(body),
      assets_scanned: assets.length,
      bytes_scanned: aggregateBytes,
      assets
    }
  };
}

export async function verifyVercelPreview(input, dependencies = {}) {
  const exact = validateInputs(input);
  if (
    input.httpTimeoutMs !== undefined &&
    (!Number.isFinite(input.httpTimeoutMs) || input.httpTimeoutMs <= 0)
  ) {
    fail("configuration", "HTTP timeout must be finite and positive.");
  }
  const polling = Object.freeze({ ...DEFAULT_POLLING, ...(input.polling ?? {}) });
  if (
    !Number.isFinite(polling.maximum_duration_ms) ||
    polling.maximum_duration_ms <= 0 ||
    polling.maximum_duration_ms > DEFAULT_POLLING.maximum_duration_ms ||
    !Number.isFinite(polling.initial_interval_ms) ||
    polling.initial_interval_ms <= 0 ||
    !Number.isFinite(polling.maximum_interval_ms) ||
    polling.maximum_interval_ms < polling.initial_interval_ms ||
    polling.maximum_interval_ms > DEFAULT_POLLING.maximum_interval_ms ||
    !Number.isFinite(polling.backoff_multiplier) ||
    polling.backoff_multiplier < 1
  ) {
    fail("configuration", "Polling policy must be finite and bounded.");
  }
  const runtime = {
    fetchImpl: dependencies.fetchImpl ?? globalThis.fetch,
    sleep: dependencies.sleep ?? ((milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))),
    now: dependencies.now ?? (() => Date.now())
  };
  if (typeof runtime.fetchImpl !== "function") {
    fail("configuration", "A Fetch implementation is required.");
  }

  const discovery = await discoverExactDeployment(input, runtime, polling);
  const deployment = await fetchAndValidateDeployment(input, discovery, runtime.fetchImpl);
  const page = await inspectProtectedPage(input, deployment, runtime.fetchImpl);
  const evidence = {
    schema_version: 1,
    phase: "F04",
    blocker_id: "f04.deployed_page_verification",
    result: "PASSED",
    verified_at: new Date(runtime.now()).toISOString(),
    expected: {
      repository: exact.repository,
      branch: exact.branch,
      git_sha: exact.expectedSha,
      project_id: exact.projectId,
      team_id: exact.teamId
    },
    discovery: {
      provider: "vercel",
      commit_status_context: "Vercel",
      github_deployment_id: discovery.githubDeploymentId,
      github_deployment_status_id: discovery.githubDeploymentStatusId,
      vercel_status_target_url: discovery.vercelStatusTargetUrl,
      polling_started_at: discovery.startedAt,
      polling_ended_at: discovery.endedAt,
      attempts: discovery.attempts,
      elapsed_ms: discovery.elapsedMs,
      final_status_context: discovery.finalStatusContext,
      final_status_state: discovery.finalStatusState,
      final_status_timestamp: discovery.finalStatusTimestamp,
      polling: discovery.polling
    },
    deployment,
    http: page.http,
    semantics: page.semantics,
    confidentiality: page.confidentiality
  };
  validateEvidence(evidence, exact);
  return evidence;
}

export function validateEvidence(evidence, expected) {
  assertExactKeys(evidence, ALLOWED_EVIDENCE_KEYS, "Evidence", "configuration");
  if (
    evidence.schema_version !== 1 ||
    evidence.phase !== "F04" ||
    evidence.blocker_id !== "f04.deployed_page_verification" ||
    evidence.result !== "PASSED"
  ) {
    fail("configuration", "Evidence schema version is unsupported.");
  }
  assertExactKeys(
    evidence.expected,
    ["repository", "branch", "git_sha", "project_id", "team_id"],
    "Evidence expected",
    "configuration"
  );
  assertExactKeys(
    evidence.discovery,
    [
      "provider",
      "commit_status_context",
      "github_deployment_id",
      "github_deployment_status_id",
      "vercel_status_target_url",
      "polling_started_at",
      "polling_ended_at",
      "attempts",
      "elapsed_ms",
      "final_status_context",
      "final_status_state",
      "final_status_timestamp",
      "polling"
    ],
    "Evidence discovery",
    "configuration"
  );
  assertExactKeys(
    evidence.discovery.polling,
    [
      "maximum_duration_ms",
      "initial_interval_ms",
      "maximum_interval_ms",
      "backoff_multiplier"
    ],
    "Evidence polling",
    "configuration"
  );
  assertExactKeys(
    evidence.deployment,
    [
      "deployment_id",
      "immutable_hostname",
      "project_id",
      "git_sha",
      "git_branch",
      "ready_state",
      "target",
      "source",
      "git_source_type",
      "created_at",
      "ready_at",
      "regions"
    ],
    "Evidence deployment",
    "configuration"
  );
  assertExactKeys(
    evidence.http,
    [
      "url",
      "status",
      "redirect_chain",
      "authentication_response",
      "content_type",
      "cache_control",
      "body_bytes",
      "body_sha256"
    ],
    "Evidence HTTP",
    "configuration"
  );
  assertExactKeys(
    evidence.semantics,
    [
      "api_state",
      "status_role_count",
      "status_label",
      "status_description_present",
      "required_copy"
    ],
    "Evidence semantics",
    "configuration"
  );
  assertExactKeys(
    evidence.confidentiality,
    [
      "forbidden_markers_absent",
      "loopback_absent",
      "health_path_absent",
      "trace_context_absent",
      "html_scanned_bytes",
      "assets_scanned",
      "bytes_scanned",
      "assets"
    ],
    "Evidence confidentiality",
    "configuration"
  );
  if (!Array.isArray(evidence.confidentiality.assets)) {
    fail("configuration", "Evidence assets must be an array.");
  }
  for (const asset of evidence.confidentiality.assets) {
    assertExactKeys(
      asset,
      ["content_type", "bytes", "sha256"],
      "Evidence asset",
      "configuration"
    );
  }
  const serialized = JSON.stringify(evidence);
  for (const forbidden of [
    "VERCEL_AUTOMATION_BYPASS_SECRET",
    "VERCEL_API_TOKEN",
    "GITHUB_TOKEN",
    "x-vercel-protection-bypass",
    "set-cookie",
    "authorization",
    "share_url",
    "shareUrl",
    "raw_html"
  ]) {
    if (serialized.toLowerCase().includes(forbidden.toLowerCase())) {
      fail("configuration", "Evidence contains forbidden credential or raw-response material.");
    }
  }
  if (expected) {
    if (
      evidence.expected?.git_sha !== expected.expectedSha ||
      evidence.expected?.repository !== expected.repository ||
      evidence.expected?.branch !== expected.branch ||
      evidence.expected?.project_id !== expected.projectId ||
      evidence.expected?.team_id !== expected.teamId
    ) {
      fail("metadata_mismatch", "Evidence expectations do not match the requested revision.");
    }
  }
  if (
    evidence.deployment?.deployment_id === undefined ||
    evidence.deployment?.git_sha !== evidence.expected?.git_sha ||
    evidence.deployment?.project_id !== evidence.expected?.project_id ||
    evidence.deployment?.ready_state !== "READY" ||
    ![null, "preview"].includes(evidence.deployment?.target) ||
    evidence.http?.status !== 200 ||
    JSON.stringify(evidence.http?.redirect_chain) !== "[200]" ||
    evidence.http?.authentication_response !== false ||
    evidence.semantics?.api_state !== "unavailable" ||
    evidence.confidentiality?.forbidden_markers_absent !== true ||
    evidence.confidentiality?.loopback_absent !== true ||
    evidence.confidentiality?.health_path_absent !== true ||
    evidence.confidentiality?.trace_context_absent !== true ||
    !Array.isArray(evidence.confidentiality?.assets) ||
    evidence.confidentiality.assets.length === 0
  ) {
    fail("metadata_mismatch", "Evidence does not prove a ready, exact-SHA protected preview.");
  }
  if (
    !/^dpl_[A-Za-z0-9]+$/.test(evidence.deployment.deployment_id) ||
    evidence.deployment.git_branch !== evidence.expected.branch ||
    evidence.deployment.source !== "git" ||
    evidence.deployment.git_source_type !== "github" ||
    !Number.isFinite(Date.parse(evidence.deployment.created_at)) ||
    !Number.isFinite(Date.parse(evidence.deployment.ready_at)) ||
    Date.parse(evidence.deployment.ready_at) < Date.parse(evidence.deployment.created_at) ||
    !Array.isArray(evidence.deployment.regions) ||
    evidence.deployment.regions.length === 0 ||
    typeof evidence.deployment.immutable_hostname !== "string" ||
    !evidence.deployment.immutable_hostname.endsWith(".vercel.app") ||
    evidence.deployment.immutable_hostname.includes("-git-") ||
    evidence.deployment.immutable_hostname === "f04-reversion-proof-web.vercel.app" ||
    evidence.http.url !== `https://${evidence.deployment.immutable_hostname}/` ||
    !/^text\/html(?:;|$)/i.test(evidence.http.content_type) ||
    !Number.isInteger(evidence.http.body_bytes) ||
    evidence.http.body_bytes <= 0 ||
    !/^[0-9a-f]{64}$/.test(evidence.http.body_sha256) ||
    evidence.discovery.provider !== "vercel" ||
    evidence.discovery.commit_status_context !== "Vercel" ||
    evidence.discovery.final_status_context !== "Vercel" ||
    evidence.discovery.final_status_state !== "success" ||
    parseInspectorDeploymentId(evidence.discovery.vercel_status_target_url) !==
      evidence.deployment.deployment_id
  ) {
    fail("metadata_mismatch", "Evidence identity or HTTP metadata is invalid.");
  }
  if (
    evidence.semantics.status_role_count !== 1 ||
    evidence.semantics.status_label !== "Local API unavailable" ||
    evidence.semantics.status_description_present !== true ||
    !Array.isArray(evidence.semantics.required_copy) ||
    !EXPECTED_VISIBLE_COPY.every((item) => evidence.semantics.required_copy.includes(item))
  ) {
    fail("semantic_mismatch", "Evidence semantic assertions are incomplete.");
  }
  const assetByteSum = evidence.confidentiality.assets.reduce(
    (sum, asset) => sum + asset.bytes,
    0
  );
  if (
    evidence.confidentiality.assets_scanned !== evidence.confidentiality.assets.length ||
    evidence.confidentiality.assets_scanned <= 0 ||
    evidence.confidentiality.assets_scanned > MAX_ASSET_COUNT ||
    evidence.confidentiality.bytes_scanned !== assetByteSum ||
    assetByteSum > MAX_AGGREGATE_ASSET_BYTES ||
    evidence.confidentiality.assets.some(
      (asset) =>
        !Number.isInteger(asset.bytes) ||
        asset.bytes <= 0 ||
        asset.bytes > MAX_ASSET_BYTES ||
        !/^(?:application|text)\/(?:javascript|css|plain)/i.test(asset.content_type) ||
        !/^[0-9a-f]{64}$/.test(asset.sha256)
    )
  ) {
    fail("confidentiality_failure", "Evidence asset assertions are invalid.");
  }
  const finitePolling = evidence.discovery?.polling;
  if (
    !Number.isFinite(finitePolling?.maximum_duration_ms) ||
    finitePolling.maximum_duration_ms <= 0 ||
    finitePolling.maximum_duration_ms > DEFAULT_POLLING.maximum_duration_ms ||
    !Number.isFinite(finitePolling?.maximum_interval_ms) ||
    finitePolling.maximum_interval_ms <= 0 ||
    finitePolling.maximum_interval_ms > DEFAULT_POLLING.maximum_interval_ms ||
    !Number.isFinite(evidence.discovery?.attempts) ||
    !Number.isInteger(evidence.discovery.attempts) ||
    evidence.discovery.attempts <= 0 ||
    !Number.isFinite(evidence.discovery.elapsed_ms) ||
    evidence.discovery.elapsed_ms < 0 ||
    evidence.discovery.elapsed_ms > finitePolling.maximum_duration_ms ||
    !Number.isFinite(Date.parse(evidence.discovery.polling_started_at)) ||
    !Number.isFinite(Date.parse(evidence.discovery.polling_ended_at)) ||
    Date.parse(evidence.discovery.polling_ended_at) <
      Date.parse(evidence.discovery.polling_started_at) ||
    !Number.isFinite(Date.parse(evidence.discovery.final_status_timestamp))
  ) {
    fail("configuration", "Evidence does not record bounded polling.");
  }
  return true;
}
