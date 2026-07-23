import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  applyVercelProjectBuildConfig,
  checkVercelProjectBuildConfig,
  VercelProjectConfigError
} from "./lib/vercel-project-build-config.mjs";

function parseArguments(argv) {
  const mode = argv[0];
  if (!["check", "apply"].includes(mode)) {
    throw new VercelProjectConfigError("configuration", "Mode must be check or apply.");
  }
  const options = {};
  for (let index = 1; index < argv.length; index += 2) {
    const name = argv[index];
    const value = argv[index + 1];
    if (!["--manifest", "--confirm-project"].includes(name) || !value) {
      throw new VercelProjectConfigError("configuration", "Project config options are invalid.");
    }
    if (options[name]) {
      throw new VercelProjectConfigError("configuration", "Project config option is duplicated.");
    }
    options[name] = value;
  }
  return { mode, options };
}

try {
  const { mode, options } = parseArguments(process.argv.slice(2));
  const defaultManifest = fileURLToPath(
    new URL("../../../plans/F04-vercel-project-build-config.json", import.meta.url)
  );
  const manifest = JSON.parse(
    await readFile(resolve(options["--manifest"] ?? defaultManifest), "utf8")
  );
  const dependencies = { token: process.env.VERCEL_API_TOKEN };
  const result =
    mode === "check"
      ? await checkVercelProjectBuildConfig(manifest, dependencies)
      : await applyVercelProjectBuildConfig(
          manifest,
          options["--confirm-project"],
          dependencies
        );
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} catch (error) {
  if (error instanceof VercelProjectConfigError) {
    process.stderr.write(`Vercel project configuration failed [${error.code}]: ${error.message}\n`);
  } else {
    process.stderr.write("Vercel project configuration failed [unexpected]: sanitized failure.\n");
  }
  process.exitCode = 1;
}
