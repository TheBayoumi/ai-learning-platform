import {
  BuildToolchainContractError,
  verifyBuildToolchain
} from "./lib/build-toolchain-contract.mjs";

try {
  const evidence = await verifyBuildToolchain();
  process.stdout.write(`${JSON.stringify(evidence)}\n`);
} catch (error) {
  if (error instanceof BuildToolchainContractError) {
    process.stderr.write(`Build toolchain verification failed [${error.code}]: ${error.message}\n`);
  } else {
    process.stderr.write("Build toolchain verification failed [unexpected]: sanitized failure.\n");
  }
  process.exitCode = 1;
}
