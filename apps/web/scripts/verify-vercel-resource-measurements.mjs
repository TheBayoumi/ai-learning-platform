import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  packageLockSha256,
  validateResourceMeasurementEvidence,
  VercelResourceMeasurementError,
  verifyVercelResourceMeasurements
} from "./lib/vercel-resource-measurement-verifier.mjs";
import { VercelBuildReproducibilityError } from "./lib/vercel-build-reproducibility-verifier.mjs";
import { VerifierError } from "./lib/vercel-preview-verifier.mjs";

const REPOSITORY_ROOT = resolve(fileURLToPath(new URL("../../../", import.meta.url)));

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
      throw new VercelResourceMeasurementError("configuration", "Resource verifier options are invalid.");
    }
    if (options[argument]) {
      throw new VercelResourceMeasurementError("configuration", "Resource verifier option is duplicated.");
    }
    options[argument] = value;
  }
  return options;
}

function sanitizedFailure(error) {
  if (error instanceof VercelResourceMeasurementError) {
    return { code: error.code, message: error.message };
  }
  if (error instanceof VercelBuildReproducibilityError) {
    return { code: `build_${error.code}`, message: error.message };
  }
  if (error instanceof VerifierError) {
    return { code: error.kind, message: error.message };
  }
  return { code: "unexpected", message: "Sanitized unexpected resource-verifier failure." };
}

let diagnosticOutput = null;

try {
  const options = parseArguments(process.argv.slice(2));
  diagnosticOutput = options["--evidence-output"] ? resolve(options["--evidence-output"]) : null;
  const requiredIdentityOptions = [
    "--expected-sha",
    "--repository",
    "--branch",
    "--project-id",
    "--team-id"
  ];
  if (requiredIdentityOptions.some((name) => !options[name])) {
    throw new VercelResourceMeasurementError(
      "configuration",
      "Exact SHA, repository, branch, project, and team options are required."
    );
  }
  const lockText = await readFile(resolve(REPOSITORY_ROOT, "apps/web/package-lock.json"), "utf8");
  if (options["--validate-evidence"]) {
    if (!options["--deployment-id"]) {
      throw new VercelResourceMeasurementError(
        "configuration",
        "--deployment-id is required for standalone evidence validation."
      );
    }
    const evidence = JSON.parse(await readFile(resolve(options["--validate-evidence"]), "utf8"));
    validateResourceMeasurementEvidence(evidence, {
      expectedSha: options["--expected-sha"],
      deploymentId: options["--deployment-id"]
    });
    process.stdout.write("Vercel resource measurement evidence is valid.\n");
  } else {
    if (!options["--evidence-output"]) {
      throw new VercelResourceMeasurementError("configuration", "--evidence-output is required.");
    }
    const evidence = await verifyVercelResourceMeasurements({
      expectedSha: options["--expected-sha"],
      repository: options["--repository"],
      branch: options["--branch"],
      projectId: options["--project-id"],
      teamId: options["--team-id"],
      githubToken: process.env.GITHUB_TOKEN,
      vercelApiToken: process.env.VERCEL_API_TOKEN,
      bypassSecret: process.env.VERCEL_AUTOMATION_BYPASS_SECRET,
      packageLockSha256: packageLockSha256(lockText)
    });
    await writeFile(resolve(options["--evidence-output"]), `${JSON.stringify(evidence, null, 2)}\n`, {
      encoding: "utf8",
      flag: "wx"
    });
    process.stdout.write("Exact-SHA Vercel resource measurement verification passed.\n");
  }
} catch (error) {
  const failure = sanitizedFailure(error);
  if (diagnosticOutput) {
    const diagnostic = {
      schema_version: 1,
      phase: "F04",
      blocker_id: "f04.resource_measurements",
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
  process.stderr.write(`Vercel resource measurements failed [${failure.code}]: ${failure.message}\n`);
  process.exitCode = 1;
}
