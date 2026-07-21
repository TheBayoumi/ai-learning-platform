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

try {
  const options = parseArguments(process.argv.slice(2));
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
  if (error instanceof VercelBuildReproducibilityError) {
    process.stderr.write(`Vercel build reproducibility failed [${error.code}]: ${error.message}\n`);
  } else if (error instanceof VerifierError) {
    process.stderr.write(`Vercel build reproducibility failed [${error.kind}]: ${error.message}\n`);
  } else if (error instanceof VercelProjectConfigError) {
    process.stderr.write(`Vercel build reproducibility failed [project_${error.code}]: ${error.message}\n`);
  } else {
    process.stderr.write("Vercel build reproducibility failed [unexpected]: sanitized failure.\n");
  }
  process.exitCode = 1;
}
