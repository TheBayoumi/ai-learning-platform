import { readFile } from "node:fs/promises";

import { beforeAll, describe, expect, it } from "vitest";

import {
  applyVercelProjectBuildConfig,
  checkVercelProjectBuildConfig,
  validateVercelProjectManifest,
  VercelProjectConfigError
} from "../scripts/lib/vercel-project-build-config.mjs";
import type { VercelProjectBuildManifest } from "../scripts/lib/vercel-project-build-config.mjs";

const PROJECT_ID = "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN";
const TEAM_ID = "team_bZWPrEPMa4sBoWU7syo3ZIRZ";
let manifest: VercelProjectBuildManifest;

beforeAll(async () => {
  manifest = JSON.parse(
    await readFile(new URL("../../../plans/F04-vercel-project-build-config.json", import.meta.url), "utf8")
  ) as VercelProjectBuildManifest;
});

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

function environment(overrides: Record<string, unknown> = {}) {
  return {
    id: "env_corepack",
    key: "ENABLE_EXPERIMENTAL_COREPACK",
    value: "1",
    type: "plain",
    target: ["preview"],
    gitBranch: "automation/f04-vercel-deployment-baseline",
    ...overrides
  };
}

function response(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}

function checkDependencies(
  projectValue = project(),
  environments: Array<Record<string, unknown>> = [environment()]
) {
  return {
    token: "test-vercel-token",
    fetchImpl: (async (resource: string | URL | Request) => {
      const url = String(resource);
      return url.includes("/env?") ? response({ envs: environments }) : response(projectValue);
    }) as typeof fetch
  };
}

describe("Vercel project build manifest", () => {
  it("accepts only the exact committed safe schema", () => {
    expect(validateVercelProjectManifest(manifest)).toBe(manifest);
    expect(() =>
      validateVercelProjectManifest({
        ...manifest,
        unexpected: true
      } as unknown as VercelProjectBuildManifest)
    ).toThrow(VercelProjectConfigError);
  });

  it("checks the exact project, Git, build, and Corepack boundaries", async () => {
    const unrelated = {
      id: "env_unrelated",
      key: "UNRELATED_PRIVATE_VALUE",
      value: "not-a-real-secret",
      type: "encrypted",
      target: ["preview"]
    };
    const result = await checkVercelProjectBuildConfig(
      manifest,
      checkDependencies(project(), [environment(), unrelated])
    );
    expect(result).toMatchObject({
      result: "PASSED",
      environment: { corepack_matches: true }
    });
    expect(JSON.stringify(result)).not.toContain("UNRELATED_PRIVATE_VALUE");
    expect(JSON.stringify(result)).not.toContain("env_unrelated");
    expect(JSON.stringify(result)).not.toContain("not-a-real-secret");
  });

  it.each([
    ["project ID", project({ id: "prj_other" }), [environment()]],
    ["team", project({ accountId: "team_other" }), [environment()]],
    ["repository", project({ link: { ...project().link, repo: "other" } }), [environment()]],
    ["root directory", project({ rootDirectory: "web" }), [environment()]],
    ["framework", project({ framework: "vite" }), [environment()]],
    ["Node setting", project({ nodeVersion: "22.x" }), [environment()]],
    ["install command", project({ installCommand: "npm install" }), [environment()]],
    ["build command", project({ buildCommand: "next build" }), [environment()]],
    ["Corepack configuration", project(), []]
  ])("fails closed on wrong %s", async (_label, projectValue, environments) => {
    await expect(
      checkVercelProjectBuildConfig(manifest, checkDependencies(projectValue, environments))
    ).rejects.toThrow(VercelProjectConfigError);
  });

  it("rejects ambiguous Corepack records", async () => {
    await expect(
      checkVercelProjectBuildConfig(
        manifest,
        checkDependencies(project(), [environment(), environment({ id: "env_two" })])
      )
    ).rejects.toThrow(/ambiguous/);
  });
});

describe("Vercel project config apply", () => {
  it("applies only allowlisted drift, verifies each mutation, and is idempotent", async () => {
    let projectState = project({ installCommand: null, buildCommand: null });
    const unrelated = {
      id: "env_unrelated",
      key: "UNRELATED_PRIVATE_VALUE",
      value: "not-a-real-secret",
      type: "encrypted",
      target: ["preview"]
    };
    let environmentState: Array<Record<string, unknown>> = [unrelated];
    const mutations: Array<{ method: string; body: Record<string, unknown> }> = [];
    const fetchImpl = (async (resource: string | URL | Request, init?: RequestInit) => {
      const url = String(resource);
      const method = init?.method ?? "GET";
      if (method === "PATCH" && !url.includes("/env/")) {
        const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
        projectState = { ...projectState, ...body };
        mutations.push({ method, body });
        return response(projectState);
      }
      if (method === "POST" && url.includes("/env?")) {
        const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
        environmentState = [...environmentState, { id: "env_corepack", ...body }];
        mutations.push({ method, body });
        return response(environmentState[0]);
      }
      return url.includes("/env?")
        ? response({ envs: environmentState })
        : response(projectState);
    }) as typeof fetch;
    const dependencies = { token: "test-vercel-token", fetchImpl };

    const first = await applyVercelProjectBuildConfig(manifest, PROJECT_ID, dependencies);
    expect(first).toMatchObject({
      result: "PASSED",
      changes: ["install_command", "build_command", "ENABLE_EXPERIMENTAL_COREPACK"]
    });
    expect(mutations).toHaveLength(2);
    expect(JSON.stringify(first)).not.toContain("test-vercel-token");
    expect(JSON.stringify(first)).not.toContain("UNRELATED_PRIVATE_VALUE");
    expect(JSON.stringify(first)).not.toContain("env_unrelated");
    expect(JSON.stringify(first)).not.toContain("not-a-real-secret");
    expect(environmentState).toContainEqual(unrelated);
    expect(mutations.some(({ method }) => method === "DELETE")).toBe(false);

    const second = await applyVercelProjectBuildConfig(manifest, PROJECT_ID, dependencies);
    expect(second).toMatchObject({ result: "PASSED", changes: [] });
    expect(mutations).toHaveLength(2);
  });

  it("refuses an unexpected project before any mutation", async () => {
    const methods: string[] = [];
    const dependencies = {
      token: "test-vercel-token",
      fetchImpl: (async (resource: string | URL | Request, init?: RequestInit) => {
        methods.push(init?.method ?? "GET");
        return String(resource).includes("/env?")
          ? response({ envs: [] })
          : response(project({ id: "prj_other" }));
      }) as typeof fetch
    };
    await expect(
      applyVercelProjectBuildConfig(manifest, PROJECT_ID, dependencies)
    ).rejects.toThrow(/refused/);
    expect(methods.every((method) => method === "GET")).toBe(true);
  });

  it("updates only the existing named Corepack record", async () => {
    let corepack = environment({ value: "0" });
    const mutationUrls: string[] = [];
    const dependencies = {
      token: "test-vercel-token",
      fetchImpl: (async (resource: string | URL | Request, init?: RequestInit) => {
        const url = String(resource);
        const method = init?.method ?? "GET";
        if (method === "PATCH" && url.includes("/env/env_corepack?")) {
          mutationUrls.push(url);
          corepack = {
            ...corepack,
            ...(JSON.parse(String(init?.body)) as Record<string, unknown>)
          };
          return response(corepack);
        }
        return url.includes("/env?") ? response({ envs: [corepack] }) : response(project());
      }) as typeof fetch
    };
    await expect(
      applyVercelProjectBuildConfig(manifest, PROJECT_ID, dependencies)
    ).resolves.toMatchObject({
      result: "PASSED",
      changes: ["ENABLE_EXPERIMENTAL_COREPACK"]
    });
    expect(mutationUrls).toHaveLength(1);
  });

  it("requires exact project confirmation", async () => {
    await expect(
      applyVercelProjectBuildConfig(manifest, "prj_wrong", checkDependencies())
    ).rejects.toThrow(/exact confirmed/);
  });
});
