import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import {
  EXIT_CODES,
  VerifierError,
  validateEvidence,
  verifyVercelPreview
} from "./lib/vercel-preview-verifier.mjs";

const DEFAULT_TEAM_ID = "team_bZWPrEPMa4sBoWU7syo3ZIRZ";

function parseArguments(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith("--")) {
      throw new VerifierError("configuration", "Unexpected positional argument.");
    }
    const name = argument.slice(2);
    if (![
      "expected-sha",
      "repository",
      "branch",
      "project-id",
      "team-id",
      "evidence-output",
      "validate-evidence"
    ].includes(name)) {
      throw new VerifierError("configuration", `Unknown option: --${name}.`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      throw new VerifierError("configuration", `Option --${name} requires a value.`);
    }
    if (options[name] !== undefined) {
      throw new VerifierError("configuration", `Option --${name} was provided more than once.`);
    }
    options[name] = value;
    index += 1;
  }
  return options;
}

async function run() {
  const options = parseArguments(process.argv.slice(2));
  const expected = {
    expectedSha: options["expected-sha"],
    repository: options.repository,
    branch: options.branch,
    projectId: options["project-id"],
    teamId: options["team-id"] ?? DEFAULT_TEAM_ID
  };

  if (options["validate-evidence"]) {
    let payload;
    try {
      payload = JSON.parse(
        await readFile(resolve(options["validate-evidence"]), "utf8")
      );
    } catch {
      throw new VerifierError(
        "configuration",
        "Evidence file could not be read as JSON."
      );
    }
    validateEvidence(payload, expected);
    process.stdout.write("Vercel preview evidence is valid.\n");
    return;
  }

  if (!options["evidence-output"]) {
    throw new VerifierError("configuration", "Option --evidence-output is required.");
  }
  const evidence = await verifyVercelPreview({
    ...expected,
    githubToken: process.env.GITHUB_TOKEN,
    vercelApiToken: process.env.VERCEL_API_TOKEN,
    bypassSecret: process.env.VERCEL_AUTOMATION_BYPASS_SECRET
  });
  try {
    const target = resolve(options["evidence-output"]);
    await writeFile(target, `${JSON.stringify(evidence, null, 2)}\n`, {
      encoding: "utf8",
      flag: "wx"
    });
  } catch {
    throw new VerifierError(
      "evidence_write_failure",
      "Sanitized evidence could not be written to the requested new file."
    );
  }
  process.stdout.write("Exact-SHA protected Vercel preview verification passed.\n");
}

try {
  await run();
} catch (error) {
  if (error instanceof VerifierError) {
    process.stderr.write(`Vercel preview verification failed [${error.kind}]: ${error.message}\n`);
    process.exitCode = error.exitCode;
  } else {
    process.stderr.write("Vercel preview verification failed [unexpected]: sanitized failure.\n");
    process.exitCode = EXIT_CODES.http_failure;
  }
}
