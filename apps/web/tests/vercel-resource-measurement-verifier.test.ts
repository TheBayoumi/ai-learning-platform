import { describe, expect, it } from "vitest";

import {
  packageLockSha256,
  validateResourceMeasurementEvidence,
  verifyVercelResourceMeasurements
} from "../scripts/lib/vercel-resource-measurement-verifier.mjs";

const SHA = "f0486d0007b8164d58a6eb680fe0729906bd4093";
const DEPLOYMENT_ID = "dpl_AUGmFfPqzRdtwH13XLirN46QgPRh";
const HOSTNAME = "web-m3163penn-mahmoudbayoumimb-7868s-projects.vercel.app";
const BYPASS_SECRET = "test".repeat(8);

const HTML = `<!doctype html><html><head>
<link rel="stylesheet" href="/_next/static/main.css">
<script src="/_next/static/main.js"></script>
</head><body><main><p>Technical foundation</p><h1>AI Career Learning Platform</h1>
<section data-api-state="unavailable"><h2>API integration</h2>
<div role="status" aria-atomic="true" aria-labelledby="api-status-label" aria-describedby="api-status-description">
<p id="api-status-label">Local API unavailable</p><p id="api-status-description">Unavailable.</p>
</div></section><section><h2>Foundation boundary</h2></section></main></body></html>`;

function logs() {
  const texts = [
    "Running build in Washington, D.C., USA (East) – iad1",
    "Build machine configuration: 2 cores, 8 GB",
    "Cloning completed: 1.958s",
    "Restored build cache from previous deployment (CacheRecord123)",
    "Vercel CLI 56.5.0",
    "added 385 packages, and audited 386 packages in 14s",
    "✓ Compiled successfully in 3.6s",
    "Finished TypeScript in 4.4s ...",
    "✓ Generating static pages using 1 worker (2/2) in 121ms",
    "Browser confidentiality check passed: 10 files, 629571 bytes.",
    "Build Completed in /vercel/output [26s]",
    "Created build cache: 16s",
    "Preparing upload\nUploading build cache [120.17 MB]\nContinuing upload",
    "Build cache uploaded: 2.334s"
  ];
  return texts.map((text, index) => ({ index, created: index, serial: index, text }));
}

function exactDeployment() {
  return {
    deployment: {
      deployment_id: DEPLOYMENT_ID,
      immutable_hostname: HOSTNAME,
      project_id: "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN",
      git_sha: SHA,
      git_branch: "automation/f04-vercel-deployment-baseline",
      ready_state: "READY",
      target: null,
      source: "git",
      git_source_type: "github",
      created_at: "2026-07-23T01:18:04.593Z",
      ready_at: "2026-07-23T01:18:40.449Z",
      regions: ["iad1"]
    },
    runtime: {
      now: () => Date.parse("2026-07-23T03:00:00.000Z"),
      sleep: async () => undefined
    }
  };
}

function input() {
  return {
    expectedSha: SHA,
    repository: "TheBayoumi/ai-learning-platform",
    branch: "automation/f04-vercel-deployment-baseline",
    projectId: "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN",
    teamId: "team_bZWPrEPMa4sBoWU7syo3ZIRZ",
    githubToken: "github-test-token",
    vercelApiToken: "vercel-test-token",
    bypassSecret: BYPASS_SECRET,
    packageLockSha256: packageLockSha256("lock")
  };
}

function dependencies(
  options: { omitCacheUpload?: boolean; delayCacheUpload?: boolean } = {}
) {
  let clock = 0;
  let pageRequests = 0;
  let collectionCalls = 0;
  const sleeps: number[] = [];
  const buildLogs = logs().filter(
    ({ text }) => !options.omitCacheUpload || !text.includes("Uploading build cache")
  );
  const fetchImpl = async (resource: string | URL | Request) => {
    const url = String(resource);
    if (url.includes("api.vercel.com/v2/teams/")) {
      return new Response(JSON.stringify({ billing: { plan: "hobby" } }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (url.includes("?f04-resource-probe=")) {
      pageRequests += 1;
      return new Response(HTML, {
        status: 200,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "x-vercel-cache": pageRequests === 1 ? "MISS" : "HIT",
          "x-vercel-id": "iad1::test"
        }
      });
    }
    if (url.endsWith("/_next/static/main.css")) {
      return new Response("body{}", {
        status: 200,
        headers: { "content-type": "text/css" }
      });
    }
    if (url.endsWith("/_next/static/main.js")) {
      return new Response("self.__next=[];", {
        status: 200,
        headers: { "content-type": "application/javascript" }
      });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };
  return {
    fetchImpl: fetchImpl as typeof fetch,
    sleep: async (milliseconds: number) => {
      sleeps.push(milliseconds);
    },
    monotonicNow: () => {
      clock += 10;
      return clock;
    },
    discoverDeployment: async () => exactDeployment(),
    collectBuildLogs: async () => {
      collectionCalls += 1;
      const selectedLogs =
        options.delayCacheUpload && collectionCalls === 1
          ? buildLogs.filter(({ text }) => !text.includes("Uploading build cache"))
          : buildLogs;
      return {
        logs: selectedLogs,
        markers: [{ node: "24.15.0", npm: "11.18.0", next_version: "16.2.10" }],
        attempts: 1
      };
    },
    sleeps
  };
}

describe("exact-SHA Vercel resource measurements", () => {
  it("records bounded build, footprint, cache, latency, runtime, and cost observations", async () => {
    const runtime = dependencies();
    const evidence = await verifyVercelResourceMeasurements(input(), runtime);

    expect(evidence).toMatchObject({
      result: "PASSED",
      expected_git_sha: SHA,
      build: {
        duration_ms: 26_000,
        deployment_elapsed_ms: 35_856,
        machine_cores: 2,
        machine_memory_mb: 8192
      },
      artifact_footprint: {
        browser_build_files: 10,
        browser_build_bytes: 629_571,
        deployed_asset_count: 2
      },
      cache: {
        restored: true,
        uploaded_bytes: 120_170_000,
        causal_speedup_claimed: false
      },
      latency: {
        classification: "first-after-bounded-quiescence",
        quiescence_ms: 60_000,
        warm_samples: expect.arrayContaining([expect.objectContaining({ status: 200 })]),
        infrastructure_cold_start_claimed: false
      },
      runtime: { node: "24.15.0", npm: "11.18.0", next: "16.2.10" },
      cost_observation: {
        team_plan: "hobby",
        preview_deployments_observed: 1,
        measurement_http_requests: 8,
        dollar_estimate_provided: false,
        bounded: true
      }
    });
    expect(evidence.latency.warm_samples).toHaveLength(5);
    expect(runtime.sleeps).toContain(60_000);
    expect(JSON.stringify(evidence)).not.toContain("test-token");
    expect(
      validateResourceMeasurementEvidence(evidence, {
        expectedSha: SHA,
        deploymentId: DEPLOYMENT_ID
      })
    ).toBe(true);
  });

  it("retries boundedly until cache-tail records propagate", async () => {
    const runtime = dependencies({ delayCacheUpload: true });
    const evidence = await verifyVercelResourceMeasurements(input(), runtime);

    expect(evidence.cache.uploaded_bytes).toBe(120_170_000);
    expect(runtime.sleeps).toContain(5_000);
  });

  it("fails closed when cache-impact evidence is incomplete", async () => {
    await expect(
      verifyVercelResourceMeasurements(input(), dependencies({ omitCacheUpload: true }))
    ).rejects.toThrow(/cache upload size/);
  });

  it("rejects altered or unbounded latency evidence", async () => {
    const evidence = await verifyVercelResourceMeasurements(input(), dependencies());
    evidence.latency.cold.total_ms = 30_001;
    expect(() =>
      validateResourceMeasurementEvidence(evidence, {
        expectedSha: SHA,
        deploymentId: DEPLOYMENT_ID
      })
    ).toThrow(/bounded range/);
  });
});
