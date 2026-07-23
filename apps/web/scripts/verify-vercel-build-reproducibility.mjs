import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  hashBuildEvidenceSources,
  validateBuildReproducibilityEvidence,
  VercelBuildReproducibilityError,
  verifyVercelBuildReproducibility
} from "./lib/vercel-build-reproducibility-verifier.mjs";
import { VerifierError } from "./lib/vercel-preview-verifier.mjs";
import {
  validateVercelProjectManifest,
  VercelProjectConfigError
} from "./lib/vercel-project-build-config.mjs";

const REPOSITORY_ROOT = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
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

function parseArguments(argv) {
  const options = {};
  const allowed = new Set([
    "expected-sha",
    "repository",
    "branch",
    "project-id",
    "team-id",
    "deployment-id",
    "evidence-output",
    "validate-evidence"
  ]);
  for (let index = 0; index < argv.length; index += 2) {
    const argument = argv[index];
    const value = argv[index + 1];
    if (!argument?.startsWith("--") || !value || !allowed.has(argument.slice(2))) {
      throw new VercelBuildReproducibilityError("configuration", "Build verifier options are invalid.");
    }
    if (options[argument]) {
      throw new VercelBuildReproducibilityError("configuration", "Build verifier option is duplicated.");
    }
    options[argument] = value;
  }
  return options;
}

function sanitizedFailure(error) {
  if (error instanceof VercelBuildReproducibilityError) {
    return { code: error.code, message: error.message };
  }
  if (error instanceof VerifierError) {
    return { code: error.kind, message: error.message };
  }
  if (error instanceof VercelProjectConfigError) {
    return { code: `project_${error.code}`, message: error.message };
  }
  return { code: "unexpected", message: "Sanitized unexpected verifier failure." };
}

let diagnosticOutput = null;

try {
  const options = parseArguments(process.argv.slice(2));
  diagnosticOutput = options["--evidence-output"]
    ? resolve(options["--evidence-output"])
    : null;
  const requiredIdentityOptions = [
    "--expected-sha",
    "--repository",
    "--branch",
    "--project-id",
    "--team-id"
  ];
  if (requiredIdentityOptions.some((name) => !options[name])) {
    throw new VercelBuildReproducibilityError(
      "configuration",
      "Exact SHA, repository, branch, project, and team options are required."
    );
  }
  const sourceEntries = await Promise.all(
    SOURCE_PATHS.map(async (path) => [path, await readFile(resolve(REPOSITORY_ROOT, path), "utf8")])
  );
  const checkedOutSource = Object.fromEntries(sourceEntries);
  const sourceHashes = hashBuildEvidenceSources(checkedOutSource);
  const projectManifest = JSON.parse(
    checkedOutSource["plans/F04-vercel-project-build-config.json"]
  );
  validateVercelProjectManifest(projectManifest);
  if (options["--validate-evidence"]) {
    if (!options["--deployment-id"]) {
      throw new VercelBuildReproducibilityError(
        "configuration",
        "--deployment-id is required for standalone evidence validation."
      );
    }
    const evidence = JSON.parse(await readFile(resolve(options["--validate-evidence"]), "utf8"));
    validateBuildReproducibilityEvidence(evidence, {
      expectedSha: options["--expected-sha"],
      repository: options["--repository"],
      branch: options["--branch"],
      projectId: options["--project-id"],
      teamId: options["--team-id"],
      deploymentId: options["--deployment-id"],
      sourceHashes
    });
    process.stdout.write("Vercel build reproducibility evidence is valid.\n");
  } else {
    if (!options["--evidence-output"]) {
      throw new VercelBuildReproducibilityError("configuration", "--evidence-output is required.");
    }
    const evidence = await verifyVercelBuildReproducibility({
      expectedSha: options["--expected-sha"],
      repository: options["--repository"],
      branch: options["--branch"],
      projectId: options["--project-id"],
      teamId: options["--team-id"],
      githubToken: process.env.GITHUB_TOKEN,
      vercelApiToken: process.env.VERCEL_API_TOKEN,
      projectManifest,
      sourceFiles: checkedOutSource
    });
    await writeFile(resolve(options["--evidence-output"]), `${JSON.stringify(evidence, null, 2)}\n`, {
      encoding: "utf8",
      flag: "wx"
    });
    process.stdout.write("Exact-SHA Vercel build reproducibility verification passed.\n");
  }
} catch (error) {
  const failure = sanitizedFailure(error);
  if (diagnosticOutput) {
    const diagnostic = {
      schema_version: 1,
      phase: "F04",
      blocker_id: "f04.build_reproducibility",
      result: "FAILED",
      code: failure.code,
      message: failure.message
    };
    try {
      await writeFile(diagnosticOutput, `${JSON.stringify(diagnostic, null, 2)}\n`, {
        encoding: "utf8",
        flag: "wx"
      });
    } catch {
      // Preserve the original verifier failure; never emit file-system details.
    }
  }
  process.stderr.write(
    `Vercel build reproducibility failed [${failure.code}]: ${failure.message}\n`
  );
  process.exitCode = 1;
}
