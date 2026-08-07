import { describe, expect, it } from "vitest";

import {
  VerifierError,
  extractStaticAssets,
  validateEvidence,
  verifyVercelPreview
} from "../scripts/lib/vercel-preview-verifier.mjs";

const SHA = "4b4d1944ee34ded8921c88222902f0de0be1fb53";
const REPOSITORY = "TheBayoumi/ai-learning-platform";
const BRANCH = "automation/f04-vercel-deployment-baseline";
const PROJECT_ID = "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN";
const TEAM_ID = "team_bZWPrEPMa4sBoWU7syo3ZIRZ";
const DEPLOYMENT_ID = "dpl_TestExactDeployment123";
const HOSTNAME = "web-testexact-mahmoudbayoumimb-7868s-projects.vercel.app";
const BYPASS_SECRET = "test".repeat(8);

const VALID_HTML = `<!doctype html>
<html><head>
  <link rel="stylesheet" href="/_next/static/main.css">
  <script src="/_next/static/main.js"></script>
</head><body>
  <main><p>Technical foundation</p><h1>AI Career Learning Platform</h1>
  <section data-api-state="unavailable"><h2>API integration</h2>
    <div role="status" aria-atomic="true" aria-labelledby="api-status-label" aria-describedby="api-status-description">
      <p id="api-status-label">Local API unavailable</p>
      <p id="api-status-description">The local API could not be confirmed.</p>
    </div>
  </section><section><h2>Foundation boundary</h2></section></main>
</body></html>`;

type Scenario = ReturnType<typeof createScenario>;

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}

function createScenario() {
  const status = {
    sha: SHA,
    statuses: [
      {
        context: "Vercel",
        state: "success",
        target_url: `https://vercel.com/team/web/${DEPLOYMENT_ID.slice(4)}`,
        created_at: "2026-07-21T10:00:00.000Z",
        updated_at: "2026-07-21T10:00:01.000Z"
      }
    ]
  };
  const deployments = [
    {
      id: 1001,
      sha: SHA,
      environment: "Preview",
      production_environment: false,
      creator: { login: "vercel[bot]" }
    }
  ];
  const deploymentStatuses = [
    {
      id: 2001,
      state: "success",
      environment_url: `https://${HOSTNAME}`,
      created_at: "2026-07-21T10:00:02.000Z",
      updated_at: "2026-07-21T10:00:03.000Z"
    }
  ];
  const vercel = {
    id: DEPLOYMENT_ID,
    projectId: PROJECT_ID,
    url: HOSTNAME,
    readyState: "READY",
    target: null,
    source: "git",
    gitSource: { type: "github", sha: SHA, ref: BRANCH },
    meta: {
      githubCommitSha: SHA,
      githubCommitRef: BRANCH,
      githubCommitOrg: "TheBayoumi",
      githubCommitRepo: "ai-learning-platform"
    },
    createdAt: Date.parse("2026-07-21T09:58:00.000Z"),
    ready: Date.parse("2026-07-21T10:00:00.000Z"),
    regions: ["iad1"]
  };
  const pages = new Map<string, Response | ((init?: RequestInit) => Promise<Response>)>([
    [
      `https://${HOSTNAME}/`,
      new Response(VALID_HTML, {
        status: 200,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "public, max-age=0"
        }
      })
    ],
    [
      `https://${HOSTNAME}/_next/static/main.css`,
      new Response("body{color:#111}", {
        status: 200,
        headers: { "content-type": "text/css" }
      })
    ],
    [
      `https://${HOSTNAME}/_next/static/main.js`,
      new Response("self.__next=[];", {
        status: 200,
        headers: { "content-type": "application/javascript" }
      })
    ]
  ]);
  return {
    status,
    deployments,
    deploymentStatuses,
    deploymentStatusResponses: null as null | unknown[],
    vercel,
    pages,
    protectedRequests: [] as RequestInit[]
  };
}

function input(overrides: Record<string, unknown> = {}) {
  return {
    expectedSha: SHA,
    repository: REPOSITORY,
    branch: BRANCH,
    projectId: PROJECT_ID,
    teamId: TEAM_ID,
    githubToken: "github-test-token",
    vercelApiToken: "vercel-test-token",
    bypassSecret: BYPASS_SECRET,
    ...overrides
  };
}

function dependencies(scenario: Scenario) {
  let time = Date.parse("2026-07-21T10:01:00.000Z");
  const fetchImpl = async (resource: string | URL | Request, init?: RequestInit) => {
    const url = String(resource);
    if (url.includes(`/commits/${SHA}/status`)) {
      return jsonResponse(scenario.status);
    }
    if (url.includes("/deployments?")) {
      return jsonResponse(scenario.deployments);
    }
    if (url.includes("/deployments/1001/statuses")) {
      const response = scenario.deploymentStatusResponses?.shift();
      return jsonResponse(response ?? scenario.deploymentStatuses);
    }
    if (url.includes("api.vercel.com/v13/deployments/")) {
      return jsonResponse(scenario.vercel);
    }
    const page = scenario.pages.get(url);
    if (page) {
      scenario.protectedRequests.push(init ?? {});
    }
    if (typeof page === "function") {
      return page(init);
    }
    if (page) {
      return page.clone();
    }
    throw new Error(`Unexpected mocked request: ${url}`);
  };
  return {
    fetchImpl: fetchImpl as typeof fetch,
    sleep: async () => undefined,
    now: () => {
      time += 10;
      return time;
    }
  };
}

async function expectFailure(
  scenario: Scenario,
  kind: string,
  overrides: Record<string, unknown> = {}
) {
  try {
    await verifyVercelPreview(input(overrides), dependencies(scenario));
  } catch (error) {
    expect(error).toBeInstanceOf(VerifierError);
    expect((error as VerifierError).kind).toBe(kind);
    return error as VerifierError;
  }
  throw new Error(`Expected ${kind} failure.`);
}

describe("exact-SHA Vercel preview verifier", () => {
  it("accepts an exact ready preview and emits deterministic sanitized evidence", async () => {
    const firstScenario = createScenario();
    const first = await verifyVercelPreview(input(), dependencies(firstScenario));
    const second = await verifyVercelPreview(input(), dependencies(createScenario()));

    expect(first).toEqual(second);
    expect(first.deployment).toMatchObject({
      deployment_id: DEPLOYMENT_ID,
      git_sha: SHA,
      ready_state: "READY",
      target: null
    });
    expect(first.http).toMatchObject({ status: 200, redirect_chain: [200] });
    expect(first.semantics).toMatchObject({ api_state: "unavailable" });
    expect(first.confidentiality).toMatchObject({
      forbidden_markers_absent: true,
      assets_scanned: 2
    });
    const serialized = JSON.stringify(first);
    expect(serialized).not.toContain(BYPASS_SECRET);
    expect(serialized).not.toContain("github-test-token");
    expect(serialized).not.toContain("vercel-test-token");
    expect(validateEvidence(first, input())).toBe(true);
    const requestHeaders = new Headers(firstScenario.protectedRequests[0]?.headers);
    expect(requestHeaders.get("x-vercel-protection-bypass")).toBe(BYPASS_SECRET);
    expect(requestHeaders.get("x-vercel-set-bypass-cookie")).toBeNull();
  });

  it("rejects a missing Vercel status after bounded polling", async () => {
    const scenario = createScenario();
    scenario.status.statuses = [];
    await expectFailure(scenario, "discovery", {
      polling: {
        maximum_duration_ms: 15,
        initial_interval_ms: 5,
        maximum_interval_ms: 5,
        backoff_multiplier: 1
      }
    });
  });

  it("rejects polling beyond the five-minute bound", async () => {
    await expectFailure(createScenario(), "configuration", {
      polling: { maximum_duration_ms: 300_001 }
    });
  });

  it("rejects a pending Vercel status after bounded polling", async () => {
    const scenario = createScenario();
    scenario.status.statuses[0].state = "pending";
    await expectFailure(scenario, "discovery", {
      polling: {
        maximum_duration_ms: 15,
        initial_interval_ms: 5,
        maximum_interval_ms: 5,
        backoff_multiplier: 1
      }
    });
  });

  it("polls until a delayed GitHub deployment status exists", async () => {
    const scenario = createScenario();
    scenario.deploymentStatusResponses = [[], scenario.deploymentStatuses];

    const evidence = await verifyVercelPreview(input(), dependencies(scenario));

    expect(evidence.discovery.attempts).toBe(2);
    expect(evidence.discovery.github_deployment_status_id).toBe(2001);
  });

  it("rejects a failed Vercel status", async () => {
    const scenario = createScenario();
    scenario.status.statuses[0].state = "failure";
    await expectFailure(scenario, "discovery");
  });

  it("rejects a status payload for another SHA", async () => {
    const scenario = createScenario();
    scenario.status.sha = "a".repeat(40);
    await expectFailure(scenario, "discovery");
  });

  it("rejects ambiguous duplicate latest Vercel statuses", async () => {
    const scenario = createScenario();
    scenario.status.statuses.push({ ...scenario.status.statuses[0] });
    await expectFailure(scenario, "discovery");
  });

  it("rejects a malformed Vercel inspector URL", async () => {
    const scenario = createScenario();
    scenario.status.statuses[0].target_url = "https://example.com/not-a-deployment";
    await expectFailure(scenario, "discovery");
  });

  it("rejects the wrong Vercel project", async () => {
    const scenario = createScenario();
    scenario.vercel.projectId = "prj_other";
    await expectFailure(scenario, "metadata_mismatch");
  });

  it.each([
    ["repository", () => {
      const scenario = createScenario();
      scenario.vercel.meta.githubCommitRepo = "other";
      return scenario;
    }],
    ["branch", () => {
      const scenario = createScenario();
      scenario.vercel.gitSource.ref = "main";
      scenario.vercel.meta.githubCommitRef = "main";
      return scenario;
    }]
  ])("rejects the wrong %s metadata", async (_label, factory) => {
    await expectFailure(factory(), "metadata_mismatch");
  });

  it("rejects a deployment that is not READY", async () => {
    const scenario = createScenario();
    scenario.vercel.readyState = "BUILDING";
    await expectFailure(scenario, "deployment_not_ready");
  });

  it("rejects a production deployment", async () => {
    const scenario = createScenario();
    (scenario.vercel as { target: string | null }).target = "production";
    await expectFailure(scenario, "metadata_mismatch");
  });

  it("rejects a mutable alias in GitHub instead of the immutable hostname", async () => {
    const scenario = createScenario();
    scenario.deploymentStatuses[0].environment_url =
      "https://web-git-automation-f04.vercel.app";
    await expectFailure(scenario, "metadata_mismatch");
  });

  it("rejects the dedicated rollback-proof alias", async () => {
    const scenario = createScenario();
    const alias = "f04-reversion-proof-web.vercel.app";
    scenario.deploymentStatuses[0].environment_url = `https://${alias}`;
    scenario.vercel.url = alias;
    await expectFailure(scenario, "metadata_mismatch");
  });

  it("rejects missing deployment Git SHA metadata", async () => {
    const scenario = createScenario();
    Reflect.deleteProperty(scenario.vercel.meta, "githubCommitSha");
    await expectFailure(scenario, "metadata_mismatch");
  });

  it("rejects a deployment SHA mismatch", async () => {
    const scenario = createScenario();
    scenario.vercel.gitSource.sha = "b".repeat(40);
    scenario.vercel.meta.githubCommitSha = "b".repeat(40);
    await expectFailure(scenario, "metadata_mismatch");
  });

  it("rejects a missing bypass secret", async () => {
    await expectFailure(createScenario(), "configuration", { bypassSecret: "" });
  });

  it("never places an encountered secret in the error", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(`${VALID_HTML}${BYPASS_SECRET}`, {
        status: 200,
        headers: { "content-type": "text/html" }
      })
    );
    const error = await expectFailure(scenario, "confidentiality_failure");
    expect(error.message).not.toContain(BYPASS_SECRET);
    expect(JSON.stringify(error.details)).not.toContain(BYPASS_SECRET);
  });

  it("rejects an HTTP authentication redirect", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response("", {
        status: 302,
        headers: { location: "https://vercel.com/sso-api" }
      })
    );
    await expectFailure(scenario, "authentication_response");
  });

  it("rejects an HTTP 200 Vercel authentication page", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response("<html>Log in to Vercel</html>", {
        status: 200,
        headers: { "content-type": "text/html" }
      })
    );
    await expectFailure(scenario, "authentication_response");
  });

  it("rejects the wrong page content type", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(VALID_HTML, {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    await expectFailure(scenario, "http_failure");
  });

  it("rejects a page beyond the response-size limit", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(VALID_HTML, {
        status: 200,
        headers: {
          "content-type": "text/html",
          "content-length": String(128 * 1024 + 1)
        }
      })
    );
    await expectFailure(scenario, "http_failure");
  });

  it("rejects a request timeout", async () => {
    const scenario = createScenario();
    scenario.pages.set(`https://${HOSTNAME}/`, (init) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new Error("aborted")));
      })
    );
    await expectFailure(scenario, "http_failure", { httpTimeoutMs: 1 });
  });

  it.each([
    ["missing status role", VALID_HTML.replace('role="status"', "")],
    ["broken ARIA references", VALID_HTML.replace("api-status-label", "missing-label")],
    ["available state", VALID_HTML.replace('data-api-state="unavailable"', 'data-api-state="available"')],
    ["invalid-response state", VALID_HTML.replace('data-api-state="unavailable"', 'data-api-state="invalid-response"')],
    ["missing status label", VALID_HTML.replace("Local API unavailable", "Unknown")]
  ])("rejects semantic mismatch: %s", async (_label, html) => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(html, { status: 200, headers: { "content-type": "text/html" } })
    );
    await expectFailure(scenario, "semantic_mismatch");
  });

  it.each([
    ["loopback origin", "http://127.0.0.1:8000"],
    ["health path", "/health/live"],
    ["diagnostic marker", "web.health.request.completed"],
    ["valid trace context", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"]
  ])("rejects confidentiality exposure: %s", async (_label, marker) => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(`${VALID_HTML}${marker}`, {
        status: 200,
        headers: { "content-type": "text/html" }
      })
    );
    await expectFailure(scenario, "confidentiality_failure");
  });

  it("does not mistake an arbitrary framework hash for trace context", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(`${VALID_HTML}${"a".repeat(64)}`, {
        status: 200,
        headers: { "content-type": "text/html" }
      })
    );
    await expect(verifyVercelPreview(input(), dependencies(scenario))).resolves.toBeDefined();
  });

  it("rejects a cross-origin browser asset", () => {
    expect(() =>
      extractStaticAssets(
        '<script src="https://cdn.example.com/app.js"></script>',
        `https://${HOSTNAME}/`
      )
    ).toThrowError(VerifierError);
  });

  it("rejects a browser asset count beyond the bound", () => {
    const html = Array.from(
      { length: 65 },
      (_, index) => `<script src="/_next/static/${index}.js"></script>`
    ).join("");
    expect(() => extractStaticAssets(html, `https://${HOSTNAME}/`)).toThrowError(
      VerifierError
    );
  });

  it("rejects a static asset beyond the per-file byte limit", async () => {
    const scenario = createScenario();
    scenario.pages.set(
      `https://${HOSTNAME}/_next/static/main.js`,
      new Response("x", {
        status: 200,
        headers: {
          "content-type": "application/javascript",
          "content-length": String(512 * 1024 + 1)
        }
      })
    );
    await expectFailure(scenario, "http_failure");
  });

  it("rejects static assets beyond the aggregate byte limit", async () => {
    const scenario = createScenario();
    const scripts = Array.from(
      { length: 5 },
      (_, index) => `<script src="/_next/static/aggregate-${index}.js"></script>`
    ).join("");
    const html = VALID_HTML.replace(
      /<link rel="stylesheet"[\s\S]*?<\/script>/,
      scripts
    );
    scenario.pages.set(
      `https://${HOSTNAME}/`,
      new Response(html, { status: 200, headers: { "content-type": "text/html" } })
    );
    for (let index = 0; index < 5; index += 1) {
      scenario.pages.set(
        `https://${HOSTNAME}/_next/static/aggregate-${index}.js`,
        new Response("x".repeat(500 * 1024), {
          status: 200,
          headers: { "content-type": "application/javascript" }
        })
      );
    }
    await expectFailure(scenario, "confidentiality_failure");
  });

  it("rejects unknown fields in sanitized evidence", async () => {
    const evidence = await verifyVercelPreview(input(), dependencies(createScenario()));
    evidence.http.unexpected = true;
    expect(() => validateEvidence(evidence, input())).toThrowError(VerifierError);
  });
});
