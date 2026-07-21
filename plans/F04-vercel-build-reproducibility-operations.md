# F04 Vercel Build Reproducibility Operations

## Scope

This runbook applies only to `f04.build_reproducibility` for the Vercel web
project `prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN` in team
`team_bZWPrEPMa4sBoWU7syo3ZIRZ`. It does not change aliases, domains,
deployment protection, production traffic, application behavior, or the API
deployment boundary.

The committed source of truth is
`plans/F04-vercel-project-build-config.json`. It requires `apps/web` as the
project root, Next.js, Vercel Node `24.x`, `npm ci`, `npm run build`, and
`ENABLE_EXPERIMENTAL_COREPACK=1` only for Preview deployments from
`automation/f04-vercel-deployment-baseline`.

## Local contract

Use Node `24.18.0` from `.nvmrc` and npm `11.18.0`. The npm version must be
selected before entering `apps/web` for dependency installation because its
`.npmrc` intentionally enables strict engine rejection.

From `apps/web`:

```powershell
npm run verify:build-toolchain
npm ci
npm test
npm run build
```

The preinstall, prebuild, and postbuild records are bounded JSON. They contain
only tool versions, lifecycle identity, the package-lock SHA-256, and safe
contract fields. A different local Node patch, a different npm patch, `npm
install`, or lockfile drift fails closed.

## Project check and apply

Provide `VERCEL_API_TOKEN` only through the process environment. Never pass it
on the command line or write it to a repository file.

```powershell
npm run vercel:config:check
npm run vercel:config:apply -- --confirm-project prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN
```

Check mode retrieves only the project and environment API surfaces needed by
the manifest. Apply mode first refuses any project/team/repository/production-
branch identity mismatch, then may change only `rootDirectory`, `framework`,
`nodeVersion`, `installCommand`, `buildCommand`, and the exact named non-secret
Corepack variable. It preserves unknown environment variables and performs a
GET verification after each mutation. Repeating apply after a matching result
must report no changes.

The live pre-implementation state already had the correct project, team, Git
repository, production branch, root, framework, and Node major; install and
build commands were unset and the Corepack variable was absent. The bounded
apply set `npm ci`, `npm run build`, and the branch-scoped Preview Corepack
record. The preferred Corepack mechanism remains conditional on exact-SHA
remote build-log proof; no fallback mechanism has been activated.

## Exact-SHA verification

The trusted branch workflow contains a separate job named `Vercel build
reproducibility`. It reuses the existing bounded GitHub deployment discovery
and Vercel metadata validation, then checks the committed project manifest and
the exact deployment's build events. It requires three ordered toolchain
records, identical lockfile hashes, Node 24, npm `11.18.0` selected through
Corepack, `npm ci`, Next.js `16.2.10`, production-build success, confidentiality
scan success, and absence of `EBADENGINE`, the broad Node-major warning, and an
unapproved fallback.

Only sanitized JSON is uploaded. Full logs, raw API responses, URLs,
authorization data, cookies, credentials, and unrelated environment records
must not enter the artifact or Git.

## Recovery

If the preferred mechanism fails, retain `f04.build_reproducibility` and record
the exact failure. Do not weaken `.npmrc`, broaden engines, suppress warnings,
or silently switch to `npm install`. A rollback of this bounded project change
restores the project install/build overrides to their prior unset values and
removes only the branch-scoped `ENABLE_EXPERIMENTAL_COREPACK` record created for
this proof. Recovery must re-read the exact project and environment record
before mutation and must not touch any other variable.

This runbook intentionally records no duration, memory, artifact-size, or
latency measurements for `f04.resource_measurements`.
