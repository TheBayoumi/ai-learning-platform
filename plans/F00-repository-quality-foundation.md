# ExecPlan: F00 Repository and Quality Foundation

**Phase:** `F00 - Repository and Quality Foundation`
**Class:** Technical foundation
**Status:** Phase passed (`Continue`)
**Decision owner:** Primary agent
**Validation lane:** `V00` remains `WAITING_HUMAN` / `Revise`; `V01` is locked.

## Objective

Create a reproducible, role-neutral monorepo baseline for the constitutionally
approved FastAPI API and Next.js web application. F00 establishes only
application structure and quality controls; it must not express a candidate
role, learner, or learning-state behavior.

## Verified Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| Governing documents exist | `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` | Met |
| Approved foundations | Technical constitution approves Python/FastAPI and Next.js/React/TypeScript | Met |
| Role-neutral scope | F00 roadmap definition and three read-only reviews | Met |
| Dedicated branch and clean starting tree | `automation/v00-phase-loop`; inspected before F00 edits | Met |
| No external V00 evidence needed | F00 is independent of candidate selection | Met |

## Scope and Layout

```text
apps/
  api/
    pyproject.toml
    uv.lock
    src/ai_learning_platform_api/
      app.py
      settings.py
      logging.py
      transport/http/health.py
      transport/http/schemas.py
    tests/
  web/
    package.json
    package-lock.json
    app/
    components/
    tests/
.github/workflows/ci.yml
```

The API exposes only configuration-only `/health/live` and `/health/ready`
operations. Readiness means the local settings and application factory are
valid; it does not imply database, queue, model, storage, authentication, or
learner readiness. The web renders a static technical shell and a non-networked
API integration placeholder. There is no browser fetch, CORS setting, API URL,
shared domain schema, server action, or API route.

## Toolchain and Dependency Rules

- Python is pinned by `.python-version` to `3.13.13`; `uv 0.11.18` manages the
  API project and committed cross-platform `uv.lock`.
- API uses currently verified FastAPI `0.139.0` and Pydantic Settings `2.14.2`;
  all runtime and developer dependencies resolve to exact lockfile versions.
- Node `24.18.0` LTS and npm `11.18.0` are pinned for CI and local version
  managers; npm manages a committed app-local `package-lock.json`.
- The web pins current verified Next.js `16.2.10`, React `19.2.7`, React DOM
  `19.2.7`, TypeScript `6.0.3`, ESLint `9.39.5`, and Vitest `4.1.10` in its
  manifest and lockfile.
- No ORM, database driver, migration tool, identity vendor, cloud/PaaS,
  object-storage, queue, telemetry exporter, LLM provider, Docker image, or
  deployment mode is selected.

## Non-Goals

- Role selection, `RoleProfile`, competency graph, curriculum, task, item,
  assessment, tutoring, simulation, mastery, evidence, or readiness behavior.
- Persistence, domain events, outbox, schemas, migrations, authentication,
  tenancy, object storage, jobs, or LLM access.
- Product flows, learner onboarding, chat, dashboards, claims, or deployment.
- F01 or any later foundation phase.

## Implementation Steps

1. Add the narrow two-lane roadmap rule and schema-v2 autonomous controller
   state without changing V00 evidence or V01 eligibility.
2. Add line-ending, ignore, toolchain, and local-command documentation.
3. Implement the minimal API factory, validated settings boundary, structured
   logging setup, typed health schemas, transport-only endpoints, and tests.
4. Implement the static App Router shell, strict TypeScript, flat ESLint config,
   Vitest configuration, component test, and production build setup.
5. Create two economical CI jobs that invoke the same locked commands as local
   development, using safe dependency caches and no external services.
6. Run the complete F00 gate, collect independent verification, repair confirmed
   defects, and record the separate validation and foundation lane states.

## Failure Handling

- Invalid API settings fail factory construction with a Pydantic validation
  error; configuration is never silently coerced.
- Health endpoints have no network or service dependency, so unavailable future
  infrastructure cannot be reported as healthy by F00.
- A lockfile mismatch fails `uv --locked` or `npm ci` rather than resolving
  opportunistically.
- A role-specific, vendor-specific, or learning-state addition fails the F00
  scope audit and returns the foundation gate to `Revise`.

## Test and CI Strategy

API checks: `uv sync --locked --all-groups`, Ruff format/lint, strict mypy,
pytest, a clean coverage run with a 95% line threshold, and a local ASGI smoke test.
Tests cover application creation, valid and invalid settings, both health
operations, typed response data, and logging initialization.

Web checks: `npm ci`, ESLint CLI, `tsc --noEmit`, Vitest, and `next build`.
The web test renders the static shell and proves the API placeholder is
non-networked.

CI runs exactly two Ubuntu jobs (API and web), with `uv` and npm dependency
caching. The documented commands also run in PowerShell on Windows and in a
POSIX shell on Linux; no shell-only task runner is required.

## Performance, Storage, and Cost

F00 has no database, external service, model call, persistent learner data, or
runtime network dependency. Health endpoints are constant-time local responses.
The only material resource cost is package installation and CI build/test time;
lockfiles and package-manager caches make those deterministic and economical.
No product latency, throughput, storage, or model-cost claim is made.

## Acceptance Criteria

1. All F00 files are role-neutral and contain no learner or role-specific
   behavior.
2. API and web dependency locks install reproducibly from a clean checkout.
3. API format, lint, strict type, unit, coverage, and smoke checks pass with at
   least 95% line coverage.
4. Web lint, strict type, unit, and production-build checks pass.
5. CI uses the same locked commands, safe caches, and no deployment or service
   credentials.
6. Repository text policy is LF in Git for source, Markdown, JSON, YAML, TOML,
   Python, TypeScript, and shell files.
7. Independent review confirms that V00 remains `WAITING_HUMAN`, V01 remains
   locked, and F00 introduced no role-specific or learning-state behavior.

## Rollback Strategy

Remove F00-only source, toolchain, CI, and documentation files together with the
narrow roadmap lane amendment. Retain all pre-existing V00 evidence and
autonomous validation-track records. No data, schema, migration, dependency
service, or external-state rollback is required.

## Gate Decision Rules

- **Continue:** all acceptance criteria and independent verification pass.
- **Revise:** a quality gate, reproducibility check, or scope audit fails.
- **Narrow:** the required foundation would constrain candidate selection or
  introduce a deferred technology.
- **Stop:** the role-neutral foundation cannot be established without bypassing
  a validation gate.

## Execution Record

- Locked API synchronization, Ruff formatting and linting, strict mypy, and a
  clean branch-coverage run passed. Pytest collected 5 tests; all passed, with
  96% total API coverage against the 95% gate.
- A real Uvicorn process became healthy in 1.18 seconds. `/health/live`,
  `/health/ready`, and `/openapi.json` returned the documented responses; the
  listener used approximately 47.8 MB working set.
- Locked web installation added 379 packages. ESLint, strict TypeScript, and 1
  Vitest test passed. The default Next.js 16.2.10 Turbopack build completed in
  7.49 seconds and produced only static `/` and `/_not-found` routes.
- The first build reproduced an environment-only failure because the Codex host
  injected unsupported `NODE_OPTIONS=--use-system-ca`. Removing that inherited
  variable made the unchanged default build pass; no Webpack fallback was added.
- Pinned `pip-audit` and `npm audit --omit=dev` checks found no known production
  dependency vulnerabilities. The Python audit used the Windows system trust
  store after the default certificate bundle rejected the local certificate chain.
- The complete intended diff passed whitespace and LF-index checks. Scope scans
  found no domain behavior, external integration, secret, machine path, or
  generated database. Generated environments and build output are ignored.
- Independent verification confirmed the API/web scope and locks, then identified
  an attribute-unaware CI EOL guard and ambiguous local-runtime documentation.
  Both were repaired; the guard now allows intentional `.bat`/`.cmd` CRLF while
  rejecting mixed or policy-inconsistent endings.
- Ubuntu GitHub Actions and the exact Node 24.18.0 runner were configured but not
  remotely executed because no commit or push was authorized. Local validation
  ran on Windows with Node 25.2.1; CI pins the supported Node 24.18.0 baseline.

**Gate decision:** `Continue`. F00 passes as a repository-quality foundation and
does not implement or authorize any product capability, V01, or F01.
