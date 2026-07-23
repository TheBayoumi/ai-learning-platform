import { readFile } from "node:fs/promises";

import { beforeAll, describe, expect, it } from "vitest";

import {
  hashBuildEvidenceSources,
  validateBuildReproducibilityEvidence,
  verifyVercelBuildReproducibility
} from "../scripts/lib/vercel-build-reproducibility-verifier.mjs";
import type { VercelProjectBuildManifest } from "../scripts/lib/vercel-project-build-config.mjs";

const SHA = "6a5f31ef4553732e4b8705583d54eee0ebb3100f";
const REPOSITORY = "TheBayoumi/ai-learning-platform";
const BRANCH = "automation/f04-vercel-deployment-baseline";
const PROJECT_ID = "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN";
const TEAM_ID = "team_bZWPrEPMa4sBoWU7syo3ZIRZ";
const DEPLOYMENT_ID = "dpl_TestBuildReproducibility123";
const HOSTNAME = "web-build-repro-mahmoudbayoumimb-7868s-projects.vercel.app";
const SOURCE_PATHS = [
  ".nvmrc",
  "package.json",
  "apps/web/.npmrc",
  "apps/web/package.json",
  "apps/web/package-lock.json",
  "apps/web/vercel.json",
  "plans/F04-vercel-project-build-config.json",
  "apps/web/scripts/lib/build-toolchain-contract.mjs",
  "apps/web/scripts/lib/vercel-build-reproducibility-verifier.mjs"
];

let sourceFiles: Record<string, string>;
let projectManifest: VercelProjectBuildManifest;

beforeAll(async () => {
  const repositoryRoot = new URL("../../../", import.meta.url);
  sourceFiles = Object.fromEntries(
    await Promise.all(
      SOURCE_PATHS.map(async (path) => [path, await readFile(new URL(path, repositoryRoot), "utf8")])
    )
  );
  projectManifest = JSON.parse(
    sourceFiles["plans/F04-vercel-project-build-config.json"]
  ) as VercelProjectBuildManifest;
});

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}

function project(overrides: Record<string, unknown> = {}) {
  return {
    id: PROJECT_ID,
    accountId: TEAM_ID,
    name: "web",
    rootDirectory: "apps/web",
    framework: "nextjs",
    nodeVersion: "24.x",
    installCommand: "npm ci",
    buildCommand: "npm run build",
    link: {
      type: "github",
      org: "TheBayoumi",
      repo: "ai-learning-platform",
      productionBranch: "main"
    },
    ...overrides
  };
}

function toolchainRecord(lifecycle: string, lockHash: string) {
  return {
    schema_version: 1,
    contract: "f04.build-toolchain",
    result: "PASSED",
    node: "24.16.1",
    npm: "11.18.0",
    environment: "vercel",
    lifecycle,
    npm_source: "corepack",
    install_command: lifecycle === "preinstall" ? "npm ci" : null,
    lockfile_version: 3,
    package_lock_sha256: lockHash,
    next_version: "16.2.10"
  };
}

type Scenario = ReturnType<typeof createScenario>;

function createScenario() {
  const lockHash = hashBuildEvidenceSources(sourceFiles)["apps/web/package-lock.json"];
  const texts: Array<string | Record<string, unknown>> = [
    "Running build in Washington, D.C., USA (East) – iad1",
    'Running "vercel build"',
    'Running "install" command: `npm ci`...',
    toolchainRecord("preinstall", lockHash),
    "Detected Next.js version: 16.2.10",
    'Running "npm run build"',
    toolchainRecord("prebuild", lockHash),
    "▲ Next.js 16.2.10 (Turbopack)",
    "✓ Compiled successfully in 3.4s",
    "Browser confidentiality check passed: 10 files, 629571 bytes.",
    toolchainRecord("postbuild", lockHash),
    "Build Completed in /vercel/output [11s]",
    "Deployment completed"
  ];
  return {
    combinedStatus: {
      sha: SHA,
      statuses: [
        {
          context: "Vercel",
          state: "success",
          target_url: `https://vercel.com/team/web/${DEPLOYMENT_ID.slice(4)}`,
          created_at: "2026-07-22T10:00:00.000Z",
          updated_at: "2026-07-22T10:00:01.000Z"
        }
      ]
    },
    githubDeployments: [
      {
        id: 1001,
        sha: SHA,
        environment: "Preview",
        production_environment: false,
        creator: { login: "vercel[bot]" }
      }
    ],
    githubDeploymentStatuses: [
      {
        id: 2001,
        state: "success",
        environment_url: `https://${HOSTNAME}`,
        created_at: "2026-07-22T10:00:02.000Z",
        updated_at: "2026-07-22T10:00:03.000Z"
      }
    ],
    deployment: {
      id: DEPLOYMENT_ID,
      projectId: PROJECT_ID,
      url: HOSTNAME,
      readyState: "READY",
      target: null as null | string,
      source: "git",
      gitSource: { type: "github", sha: SHA, ref: BRANCH },
      meta: {
        githubCommitSha: SHA,
        githubCommitRef: BRANCH,
        githubCommitOrg: "TheBayoumi",
        githubCommitRepo: "ai-learning-platform"
      },
      createdAt: Date.parse("2026-07-22T09:58:00.000Z"),
      ready: Date.parse("2026-07-22T10:00:00.000Z"),
      regions: ["iad1"]
    },
    project: project(),
    environments: [
      {
        id: "env_corepack",
        key: "ENABLE_EXPERIMENTAL_COREPACK",
        value: "1",
        type: "plain",
        target: ["preview"],
        gitBranch: BRANCH
      }
    ],
    events: texts.map((text, index) => ({
      type: "stdout",
      created: Date.parse("2026-07-22T10:01:00.000Z") + index,
      payload: {
        deploymentId: DEPLOYMENT_ID,
        serial: index,
        text: typeof text === "string" ? text : JSON.stringify(text)
      }
    }))
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
    projectManifest,
    sourceFiles,
    ...overrides
  };
}

function dependencies(scenario: Scenario) {
  let now = Date.parse("2026-07-22T10:02:00.000Z");
  return {
    fetchImpl: (async (resource: string | URL | Request) => {
      const url = String(resource);
      if (url.includes(`/commits/${SHA}/status`)) return jsonResponse(scenario.combinedStatus);
      if (url.includes("api.github.com") && url.includes("/deployments?")) {
        return jsonResponse(scenario.githubDeployments);
      }
      if (url.includes("api.github.com") && url.includes("/deployments/1001/statuses")) {
        return jsonResponse(scenario.githubDeploymentStatuses);
      }
      if (url.includes("/v13/deployments/")) return jsonResponse(scenario.deployment);
      if (url.includes(`/v3/deployments/${DEPLOYMENT_ID}/events?`)) {
        const requestUrl = new URL(url);
        if (
          requestUrl.searchParams.get("direction") !== "forward" ||
          requestUrl.searchParams.get("follow") !== "0" ||
          requestUrl.searchParams.get("limit") !== "2000" ||
          requestUrl.searchParams.get("teamId") !== TEAM_ID
        ) {
          throw new Error(`Unexpected Vercel events query: ${url}`);
        }
        return jsonResponse(scenario.events);
      }
      if (url.includes("/v9/projects/") && url.includes("/env?")) {
        return jsonResponse({ envs: scenario.environments });
      }
      if (url.includes("/v9/projects/")) return jsonResponse(scenario.project);
      throw new Error(`Unexpected mocked request: ${url}`);
    }) as typeof fetch,
    sleep: async () => undefined,
    now: () => {
      now += 10;
      return now;
    }
  };
}

function marker(scenario: Scenario, lifecycle: string) {
  const event = scenario.events.find((item) => item.payload.text.includes(`"lifecycle":"${lifecycle}"`));
  if (!event) throw new Error("Missing test marker");
  return JSON.parse(event.payload.text);
}

function replaceMarker(scenario: Scenario, lifecycle: string, value: Record<string, unknown>) {
  const event = scenario.events.find((item) => item.payload.text.includes(`"lifecycle":"${lifecycle}"`));
  if (!event) throw new Error("Missing test marker");
  event.payload.text = JSON.stringify(value);
}

function evidenceExpectations() {
  return {
    expectedSha: SHA,
    repository: REPOSITORY,
    branch: BRANCH,
    projectId: PROJECT_ID,
    teamId: TEAM_ID,
    deploymentId: DEPLOYMENT_ID,
    sourceHashes: hashBuildEvidenceSources(sourceFiles)
  };
}

describe("exact-SHA Vercel build reproducibility", () => {
  it("proves the exact deployment, project manifest, toolchain, locked install, and build", async () => {
    const scenario = createScenario();
    const evidence = await verifyVercelBuildReproducibility(input(), dependencies(scenario));
    expect(evidence).toMatchObject({
      result: "PASSED",
      expected_git_sha: SHA,
      deployment: {
        deployment_id: DEPLOYMENT_ID,
        observed_node: "24.16.1",
        observed_npm: "11.18.0"
      },
      build_assertions: { locked_install: true, lockfile_unchanged: true }
    });
    expect(JSON.stringify(evidence)).not.toContain("test-token");
  });

  it("binds the repository-root Corepack manifest into durable evidence", async () => {
    const evidence = await verifyVercelBuildReproducibility(
      input(),
      dependencies(createScenario())
    );
    expect(evidence).toMatchObject({
      repository_contract: {
        package_manager_source: "package.json",
        package_manager: "npm@11.18.0"
      }
    });
    expect((evidence.source_hashes as Record<string, string>)["package.json"]).toMatch(
      /^[0-9a-f]{64}$/
    );
  });

  it.each([
    ["wrong Git SHA", (scenario: Scenario) => (scenario.deployment.meta.githubCommitSha = "0".repeat(40))],
    ["non-ready deployment", (scenario: Scenario) => (scenario.deployment.readyState = "BUILDING")],
    ["production deployment", (scenario: Scenario) => (scenario.deployment.target = "production")],
    ["wrong branch", (scenario: Scenario) => (scenario.deployment.meta.githubCommitRef = "main")],
    ["wrong project", (scenario: Scenario) => (scenario.project = project({ id: "prj_other" }))],
    ["wrong root", (scenario: Scenario) => (scenario.project = project({ rootDirectory: "web" }))],
    ["wrong framework", (scenario: Scenario) => (scenario.project = project({ framework: "vite" }))],
    ["wrong Node setting", (scenario: Scenario) => (scenario.project = project({ nodeVersion: "22.x" }))],
    ["missing Corepack", (scenario: Scenario) => (scenario.environments = [])]
  ])("fails closed on %s", async (_label, mutate) => {
    const scenario = createScenario();
    mutate(scenario);
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(scenario))
    ).rejects.toThrow();
  });

  it("times out a stale deployment status under bounded polling", async () => {
    const scenario = createScenario();
    scenario.combinedStatus.statuses[0].state = "pending";
    await expect(
      verifyVercelBuildReproducibility(
        input({
          polling: {
            maximum_duration_ms: 20,
            initial_interval_ms: 10,
            maximum_interval_ms: 10,
            backoff_multiplier: 1
          }
        }),
        dependencies(scenario)
      )
    ).rejects.toThrow(/timed out/);
  });

  it("rejects missing and ambiguous build logs", async () => {
    const missing = createScenario();
    missing.events = [];
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(missing))
    ).rejects.toThrow(/missing or unbounded/);

    const ambiguous = createScenario();
    const duplicate = structuredClone(
      ambiguous.events.find((event) => event.payload.text.includes('"lifecycle":"prebuild"'))!
    );
    ambiguous.events.push(duplicate);
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(ambiguous))
    ).rejects.toThrow(/ambiguous|exactly three/);
  });

  it.each([
    ["EBADENGINE", "npm warn EBADENGINE Unsupported engine"],
    ["broad Node warning", "will automatically upgrade when a new major Node.js Version is released"],
    ["npm install fallback", 'Running "npm install"'],
    ["custom npm fallback", "npm install --global npm@11.18.0"]
  ])("rejects %s", async (_label, text) => {
    const scenario = createScenario();
    scenario.events.push({
      type: "stderr",
      created: Date.now(),
      payload: { deploymentId: DEPLOYMENT_ID, serial: 99, text }
    });
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(scenario))
    ).rejects.toThrow();
  });

  it("rejects wrong npm and lockfile mutation records", async () => {
    const wrongNpm = createScenario();
    replaceMarker(wrongNpm, "preinstall", { ...marker(wrongNpm, "preinstall"), npm: "11.12.1" });
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(wrongNpm))
    ).rejects.toThrow(/preinstall/);

    const mutation = createScenario();
    replaceMarker(mutation, "postbuild", {
      ...marker(mutation, "postbuild"),
      package_lock_sha256: "f".repeat(64)
    });
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(mutation))
    ).rejects.toThrow(/postbuild/);
  });

  it("rejects build and confidentiality failures", async () => {
    const failedBuild = createScenario();
    failedBuild.events = failedBuild.events.filter(
      (event) => !event.payload.text.includes("Compiled successfully")
    );
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(failedBuild))
    ).rejects.toThrow(/compilation/);

    const failedScan = createScenario();
    failedScan.events = failedScan.events.filter(
      (event) => !event.payload.text.startsWith("Browser confidentiality check passed:")
    );
    await expect(
      verifyVercelBuildReproducibility(input(), dependencies(failedScan))
    ).rejects.toThrow(/confidentiality/);
  });

  it("rejects authorization or secret material added to evidence", async () => {
    const evidence = await verifyVercelBuildReproducibility(
      input(),
      dependencies(createScenario())
    );
    (evidence.repository_contract as Record<string, unknown>).api_token = "forbidden";
    expect(() => validateBuildReproducibilityEvidence(evidence)).toThrow(
      /safe schema|forbidden material/
    );
  });

  it("rejects evidence detached from the checked-out source hashes", async () => {
    const evidence = await verifyVercelBuildReproducibility(
      input(),
      dependencies(createScenario())
    );
    (evidence.source_hashes as Record<string, string>)["apps/web/package.json"] = "f".repeat(64);
    expect(() =>
      validateBuildReproducibilityEvidence(evidence, evidenceExpectations())
    ).toThrow(/checked-out source/);
  });

  it.each([
    ["project ID", "vercel_project", "project_id", "prj_other"],
    ["team ID", "vercel_project", "team_id", "team_other"],
    ["project root", "vercel_project", "root_directory", "web"],
    ["framework", "vercel_project", "framework", "vite"],
    ["Node setting", "vercel_project", "node_setting", "22.x"],
    ["deployment ID", "deployment", "deployment_id", "dpl_other"],
    ["Git branch", "deployment", "git_branch", "main"],
    ["repository", "deployment", "repository", "Other/repository"]
  ])("rejects altered durable evidence identity: %s", async (_label, section, field, value) => {
    const evidence = await verifyVercelBuildReproducibility(
      input(),
      dependencies(createScenario())
    );
    ((evidence as Record<string, unknown>)[section] as Record<string, unknown>)[field] = value;
    expect(() =>
      validateBuildReproducibilityEvidence(evidence, evidenceExpectations())
    ).toThrow(/required contract/);
  });
});
