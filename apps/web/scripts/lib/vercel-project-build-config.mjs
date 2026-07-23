const MAX_JSON_BYTES = 256 * 1024;
const PROJECT_KEYS = Object.freeze([
  "id",
  "team_id",
  "name",
  "root_directory",
  "framework",
  "node_version",
  "production_branch",
  "git_repository"
]);
const BUILD_KEYS = Object.freeze([
  "package_manager",
  "install_command",
  "build_command",
  "lockfile"
]);
const COREPACK_KEYS = Object.freeze([
  "required",
  "value",
  "targets",
  "git_branch"
]);

export class VercelProjectConfigError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "VercelProjectConfigError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new VercelProjectConfigError(code, message);
}

function requireObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    fail("schema", `${label} must be an object.`);
  }
  return value;
}

function assertExactKeys(value, expected, label) {
  const object = requireObject(value, label);
  const actual = Object.keys(object).sort();
  const wanted = [...expected].sort();
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
    fail("schema", `${label} keys do not match the committed schema.`);
  }
  return object;
}

function requireExact(value, expected, label) {
  if (value !== expected) {
    fail("schema", `${label} differs from the approved F04 value.`);
  }
}

export function validateVercelProjectManifest(manifest) {
  assertExactKeys(
    manifest,
    ["schema_version", "project", "build", "environment"],
    "Manifest"
  );
  requireExact(manifest.schema_version, 1, "schema_version");
  const project = assertExactKeys(manifest.project, PROJECT_KEYS, "Manifest project");
  const build = assertExactKeys(manifest.build, BUILD_KEYS, "Manifest build");
  const environment = assertExactKeys(
    manifest.environment,
    ["ENABLE_EXPERIMENTAL_COREPACK"],
    "Manifest environment"
  );
  const corepack = assertExactKeys(
    environment.ENABLE_EXPERIMENTAL_COREPACK,
    COREPACK_KEYS,
    "Corepack configuration"
  );

  const expected = {
    project: {
      id: "prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN",
      team_id: "team_bZWPrEPMa4sBoWU7syo3ZIRZ",
      name: "web",
      root_directory: "apps/web",
      framework: "nextjs",
      node_version: "24.x",
      production_branch: "main",
      git_repository: "TheBayoumi/ai-learning-platform"
    },
    build: {
      package_manager: "npm@11.18.0",
      install_command: "npm ci",
      build_command: "npm run build",
      lockfile: "apps/web/package-lock.json"
    },
    corepack: {
      required: true,
      value: "1",
      targets: ["preview"],
      git_branch: "automation/f04-vercel-deployment-baseline"
    }
  };
  for (const [key, value] of Object.entries(expected.project)) {
    requireExact(project[key], value, `project.${key}`);
  }
  for (const [key, value] of Object.entries(expected.build)) {
    requireExact(build[key], value, `build.${key}`);
  }
  for (const [key, value] of Object.entries(expected.corepack)) {
    if (Array.isArray(value)) {
      if (JSON.stringify(corepack[key]) !== JSON.stringify(value)) {
        fail("schema", `environment.ENABLE_EXPERIMENTAL_COREPACK.${key} differs.`);
      }
    } else {
      requireExact(corepack[key], value, `environment.ENABLE_EXPERIMENTAL_COREPACK.${key}`);
    }
  }
  return manifest;
}

async function requestJson(fetchImpl, token, url, options = {}) {
  if (typeof token !== "string" || token.length === 0) {
    fail("configuration", "VERCEL_API_TOKEN is required.");
  }
  let response;
  try {
    response = await fetchImpl(url, {
      method: options.method ?? "GET",
      headers: {
        authorization: `Bearer ${token}`,
        ...(options.body ? { "content-type": "application/json" } : {})
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      redirect: "manual"
    });
  } catch {
    fail("api", "Vercel project configuration request failed.");
  }
  if (!response.ok) {
    fail("api", `Vercel project configuration request returned HTTP ${response.status}.`);
  }
  const text = await response.text();
  if (Buffer.byteLength(text) > MAX_JSON_BYTES) {
    fail("api", "Vercel project configuration response exceeded the size limit.");
  }
  try {
    return text.length === 0 ? {} : JSON.parse(text);
  } catch {
    fail("api", "Vercel project configuration response was not valid JSON.");
  }
}

function projectUrl(manifest) {
  return `https://api.vercel.com/v9/projects/${manifest.project.id}?teamId=${encodeURIComponent(manifest.project.team_id)}`;
}

function environmentUrl(manifest) {
  return `https://api.vercel.com/v9/projects/${manifest.project.id}/env?teamId=${encodeURIComponent(manifest.project.team_id)}`;
}

function environmentCreateUrl(manifest) {
  return `https://api.vercel.com/v10/projects/${manifest.project.id}/env?teamId=${encodeURIComponent(manifest.project.team_id)}&upsert=true`;
}

function environmentRecordUrl(manifest, environmentId) {
  return `https://api.vercel.com/v9/projects/${manifest.project.id}/env/${encodeURIComponent(environmentId)}?teamId=${encodeURIComponent(manifest.project.team_id)}`;
}

function observedProject(payload) {
  const link = requireObject(payload.link, "Vercel project Git link");
  return {
    id: payload.id ?? null,
    team_id: payload.accountId ?? null,
    name: payload.name ?? null,
    root_directory: payload.rootDirectory ?? null,
    framework: payload.framework ?? null,
    node_version: payload.nodeVersion ?? null,
    production_branch: link.productionBranch ?? null,
    git_repository:
      typeof link.org === "string" && typeof link.repo === "string"
        ? `${link.org}/${link.repo}`
        : null,
    git_type: link.type ?? null,
    install_command: payload.installCommand ?? null,
    build_command: payload.buildCommand ?? null
  };
}

function corepackRecord(payload) {
  const entries = Array.isArray(payload.envs) ? payload.envs : Array.isArray(payload) ? payload : null;
  if (!entries) {
    fail("api", "Vercel environment response is malformed.");
  }
  const matches = entries.filter((entry) => entry?.key === "ENABLE_EXPERIMENTAL_COREPACK");
  if (matches.length > 1) {
    fail("ambiguous", "Corepack environment configuration is ambiguous.");
  }
  return matches[0] ?? null;
}

function compareSnapshot(manifest, projectPayload, environmentPayload) {
  const project = observedProject(projectPayload);
  const corepack = corepackRecord(environmentPayload);
  const expectedCorepack = manifest.environment.ENABLE_EXPERIMENTAL_COREPACK;
  const mismatches = [];
  const expectedProject = manifest.project;
  const mapping = {
    id: expectedProject.id,
    team_id: expectedProject.team_id,
    name: expectedProject.name,
    root_directory: expectedProject.root_directory,
    framework: expectedProject.framework,
    node_version: expectedProject.node_version,
    production_branch: expectedProject.production_branch,
    git_repository: expectedProject.git_repository,
    git_type: "github",
    install_command: manifest.build.install_command,
    build_command: manifest.build.build_command
  };
  for (const [field, expected] of Object.entries(mapping)) {
    if (project[field] !== expected) {
      mismatches.push(field);
    }
  }
  const target = Array.isArray(corepack?.target) ? [...corepack.target].sort() : [];
  const expectedTarget = [...expectedCorepack.targets].sort();
  const corepackMatches =
    corepack?.value === expectedCorepack.value &&
    corepack?.type === "plain" &&
    JSON.stringify(target) === JSON.stringify(expectedTarget) &&
    corepack?.gitBranch === expectedCorepack.git_branch;
  if (!corepackMatches) {
    mismatches.push("ENABLE_EXPERIMENTAL_COREPACK");
  }
  return {
    result: mismatches.length === 0 ? "PASSED" : "DRIFT",
    project,
    environment: {
      corepack_present: corepack !== null,
      corepack_matches: corepackMatches,
      targets: corepackMatches ? expectedTarget : [],
      git_branch_matches: corepack?.gitBranch === expectedCorepack.git_branch
    },
    mismatches: mismatches.sort(),
    corepackId: typeof corepack?.id === "string" ? corepack.id : null
  };
}

function sanitized(snapshot) {
  return {
    result: snapshot.result,
    project: snapshot.project,
    environment: snapshot.environment,
    mismatches: snapshot.mismatches
  };
}

async function fetchSnapshot(manifest, dependencies) {
  const fetchImpl = dependencies.fetchImpl ?? globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    fail("configuration", "A Fetch implementation is required.");
  }
  const [projectPayload, environmentPayload] = await Promise.all([
    requestJson(fetchImpl, dependencies.token, projectUrl(manifest)),
    requestJson(fetchImpl, dependencies.token, environmentUrl(manifest))
  ]);
  return compareSnapshot(manifest, projectPayload, environmentPayload);
}

export async function checkVercelProjectBuildConfig(manifest, dependencies = {}) {
  validateVercelProjectManifest(manifest);
  const snapshot = await fetchSnapshot(manifest, dependencies);
  if (snapshot.result !== "PASSED") {
    fail("drift", `Vercel project configuration differs: ${snapshot.mismatches.join(", ")}.`);
  }
  return sanitized(snapshot);
}

function assertMutationIdentity(manifest, snapshot, confirmation) {
  if (confirmation !== manifest.project.id) {
    fail("confirmation", "Apply requires the exact confirmed Vercel project ID.");
  }
  const identity = [
    ["id", manifest.project.id],
    ["team_id", manifest.project.team_id],
    ["name", manifest.project.name],
    ["git_type", "github"],
    ["git_repository", manifest.project.git_repository],
    ["production_branch", manifest.project.production_branch]
  ];
  for (const [field, expected] of identity) {
    if (snapshot.project[field] !== expected) {
      fail("refused", `Apply refused because ${field} identifies another project boundary.`);
    }
  }
}

export async function applyVercelProjectBuildConfig(
  manifest,
  confirmation,
  dependencies = {}
) {
  validateVercelProjectManifest(manifest);
  const fetchImpl = dependencies.fetchImpl ?? globalThis.fetch;
  const initial = await fetchSnapshot(manifest, { ...dependencies, fetchImpl });
  assertMutationIdentity(manifest, initial, confirmation);
  const changes = [];
  const mutable = {
    root_directory: ["rootDirectory", manifest.project.root_directory],
    framework: ["framework", manifest.project.framework],
    node_version: ["nodeVersion", manifest.project.node_version],
    install_command: ["installCommand", manifest.build.install_command],
    build_command: ["buildCommand", manifest.build.build_command]
  };
  const projectPatch = {};
  for (const [observedField, [apiField, expected]] of Object.entries(mutable)) {
    if (initial.project[observedField] !== expected) {
      projectPatch[apiField] = expected;
      changes.push(observedField);
    }
  }
  if (Object.keys(projectPatch).length > 0) {
    await requestJson(fetchImpl, dependencies.token, projectUrl(manifest), {
      method: "PATCH",
      body: projectPatch
    });
    const afterProject = await fetchSnapshot(manifest, { ...dependencies, fetchImpl });
    for (const field of Object.keys(mutable)) {
      if (field !== "ENABLE_EXPERIMENTAL_COREPACK" && afterProject.mismatches.includes(field)) {
        fail("verification", "Vercel project mutation did not persist the expected value.");
      }
    }
  }

  let current = await fetchSnapshot(manifest, { ...dependencies, fetchImpl });
  if (!current.environment.corepack_matches) {
    const corepack = manifest.environment.ENABLE_EXPERIMENTAL_COREPACK;
    const body = {
      key: "ENABLE_EXPERIMENTAL_COREPACK",
      value: corepack.value,
      type: "plain",
      target: corepack.targets,
      gitBranch: corepack.git_branch
    };
    if (current.corepackId) {
      await requestJson(
        fetchImpl,
        dependencies.token,
        environmentRecordUrl(manifest, current.corepackId),
        { method: "PATCH", body }
      );
    } else {
      await requestJson(
        fetchImpl,
        dependencies.token,
        environmentCreateUrl(manifest),
        { method: "POST", body }
      );
    }
    changes.push("ENABLE_EXPERIMENTAL_COREPACK");
    current = await fetchSnapshot(manifest, { ...dependencies, fetchImpl });
    if (!current.environment.corepack_matches) {
      fail("verification", "Corepack configuration mutation did not persist.");
    }
  }

  if (current.result !== "PASSED") {
    fail("verification", `Vercel project still differs: ${current.mismatches.join(", ")}.`);
  }
  return {
    schema_version: 1,
    result: "PASSED",
    changes,
    before: sanitized(initial),
    after: sanitized(current)
  };
}
