# Codex agent package for the AI Career Learning Platform

Copy the contents of this directory into the repository root:

```text
AGENTS.md
.codex/
  config.toml
  agents/
    architecture-guardian.toml
    learning-evidence-reviewer.toml
    mission-guardian.toml
    phase-worker.toml
    roadmap-gate-reviewer.toml
    verification-reviewer.toml
```

The custom agents intentionally omit `model` and `model_reasoning_effort`, so they inherit the model and intelligence/reasoning level selected by the parent Codex session.

Suggested first command:

```text
Review the current repository against AGENTS.md and the three specs. Delegate mission, learning-evidence, architecture, and roadmap reviews in parallel. Continue your own repository inspection while they run, wait for all completed reviews before finalizing, then return one prioritized implementation recommendation. Do not modify files.
```

Suggested phase implementation command:

```text
Implement roadmap phase <PHASE_ID>. First delegate read-only exploration and the relevant constitutional reviews. Create or update a self-contained ExecPlan, then use only one phase_worker for edits. Run verification_reviewer after implementation, reconcile confirmed findings, execute all affected checks, and report the gate disposition. Do not begin the next phase.
```

## F00 local development

F00 is a role-neutral repository and quality foundation. `V00` remains the
validation lane and `V01` remains locked; the health endpoints report only local
process/configuration status, not product or learner readiness.

Use Python 3.13.13 with uv 0.11.18 and Node 24.18.0 with npm 11.18.0.
Run the same quality checks used by CI from the directories shown below.

From `apps/api`:

```powershell
uv sync --locked --all-groups
uv run --locked ruff format --check . ../../scripts
uv run --locked ruff check . ../../scripts
uv run --locked mypy src tests ../../scripts
uv run --locked coverage erase
uv run --locked coverage run -m pytest
uv run --locked coverage report --fail-under=95
```

For a local runtime smoke check from `apps/api`, start the API with
`uv run --locked uvicorn ai_learning_platform_api.main:app --no-access-log`. Stop it after
checking `/health/live`, `/health/ready`, and `/openapi.json`. The F00 API quality
job does not run a long-lived server; F01-06 defines the owned cross-process
local/CI smoke below.

From `apps/web`:

```powershell
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

From the repository root:

```powershell
git diff --check
git ls-files --eol
git status --short --branch
```

The API and web commands intentionally use no root-level path assumptions. The
static web shell starts with `npm run dev` from `apps/web`. F00 keeps Next.js's
default Turbopack build; if host tooling injects an unsupported `NODE_OPTIONS`,
clear that host variable rather than changing the repository build command. CI
does not set `NODE_OPTIONS`.

## F01 health OpenAPI contract

F01-01 tracks a canonical artifact generated directly from the FastAPI
application. It adds no web networking, API location, process supervisor, domain
schema, or product behavior. From `apps/api`, intentionally regenerate it with:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi write openapi/health.openapi.json
```

Verify that the committed bytes still match runtime generation with:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi check openapi/health.openapi.json
```

Check mode is non-mutating and returns a nonzero exit code for a missing or
drifted artifact. CI runs this exact locked check command before API quality
checks. Regeneration must be reviewed and committed intentionally.

F01-02 derives a dependency-free TypeScript type guard from that canonical
artifact. It contains no API URL, fetch, environment access, React, or UI state.
From `apps/api`, intentionally regenerate it with:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_typescript write openapi/health.openapi.json ../web/server/contracts/generated/health-response.ts
```

Run the identical non-mutating check used by CI with:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_typescript check openapi/health.openapi.json ../web/server/contracts/generated/health-response.ts
```

The generator fails closed on unsupported OpenAPI or JSON Schema features rather
than silently approximating them.

F01-03 adds a server-only local health adapter. The API origin is read from
`AI_PLATFORM_API_BASE_URL`; when it is absent, the deterministic development
default is `http://127.0.0.1:8000`. An explicit value must be a canonical HTTP
origin with an explicit port and the literal host `127.0.0.1` or `[::1]`.
Credentials, DNS names (including `localhost`), remote or wildcard addresses,
paths, queries, fragments, HTTPS, and normalized aliases fail configuration
before networking. Copy `apps/web/.env.example` for the documented local value;
never expose it through a `NEXT_PUBLIC_*` variable.

The replaceable adapter calls only `GET /health/live` through an injected fetch,
omits credentials, rejects redirects, disables caching, and requires an exact
HTTP 200 JSON response accepted by the generated guard. Callers must provide a
positive bounded timeout; F01-04 will select and record the provisional local UI
deadline. Results expose only `available`, `unavailable`, or `invalid-response`
classification and safe reason codes, never the response body, health detail,
status code, URL, or exception text.

F01-04 uses that adapter from the request-time rendered home route with one
attempt and a provisional 2,000 ms local UI deadline. This is an operational
safety bound, not a latency guarantee. The server passes only the classification
to the presentational shell, which renders distinct accessible text for local API
available, unavailable, or invalid-response states. Invalid configuration and
unexpected server defects remain visible request failures rather than being
misreported as API unavailability.

The status is a snapshot from the most recent server render, not live monitoring.
Reload to request a new check. The browser receives no API origin, health path,
reason code, response detail, client fetch, polling, or retry behavior. An
available state proves only the local liveness contract; it does not describe
product or learner state.

F01-05 adds one development-only supervisor for both local processes. After the
locked API and web installs above, run this command from the repository root:

```powershell
python scripts/dev.py
```

The command accepts no arguments. It launches the API on `127.0.0.1:8000` through
locked `uv run` and the pinned Next.js CLI on `127.0.0.1:3000`, with native child
output left visible. “Processes launched” does not claim readiness. Press
`Ctrl+C` to request bounded cleanup of both owned process trees. On Windows,
each suspended child is assigned to its own kill-on-close Job Object before it
is resumed, so descendants remain owned even if their direct parent exits.

Clean operator shutdown returns zero. A child launch failure or unexpected exit
identifies the service, stops its sibling tree, and returns nonzero; ordinary
child codes 1 through 125 are preserved. The supervisor does not probe HTTP,
restart processes, scan ports for ownership, detach, or provide production
process management. The separate F01-06 command below owns the HTTP and CI smoke
process management. Cross-process health smoke and CI smoke remain F01-06.

F01-06 adds one deterministic cross-process smoke command. After the same
locked API and web installs, run it from the repository root:

```powershell
uv run --project apps/api --locked python scripts/smoke.py
```

The command accepts no arguments, requires fixed loopback ports 8000 and 3000
to be unused, and applies a 45-second shared startup deadline, 5-second request
timeouts, and a 1 MiB response limit. It owns both process trees through the
F01-05 lifecycle primitives and always performs bounded cleanup.

A zero exit proves only that this invocation observed the exact liveness and
configuration-only readiness payloads, runtime OpenAPI equality with the tracked
canonical artifact, and the accessible server-rendered available state without
server-only values. It also proves that cleanup succeeded and both fixed ports
closed. It does not prove product, learner, mastery, or role readiness. Startup,
contract, process-exit, interruption, cleanup, or port-closure failure returns
nonzero without echoing response bodies or private exception details.

## F02 confidential health diagnostics

F02-01 and F02-02 add one exporter-free W3C/OpenTelemetry diagnostic chain only
for the existing server-rendered `GET /health/live` transaction. The Next.js
server creates one private client span and sends exactly one canonical
`traceparent`; the API creates a distinct server span in the same trace. Both
processes emit one compact allowlisted completion event to their server logs.
There is no global provider registration, browser tracing, automatic route
instrumentation, exporter, telemetry backend, persistence, or network egress.

The events contain only fixed classifications, validated trace/span IDs, HTTP
status, and elapsed milliseconds. They never contain the configured API origin,
URL, request or response headers, body, health detail, exception text,
environment values, cookies, learner data, or product identifiers.
Instrumentation failure may remove a diagnostic record but cannot change the
health result. `npm run build` now scans `.next/static` and fails if web
diagnostic or API-configuration markers enter browser assets. This diagnostic
baseline is not monitoring, analytics, audit evidence, a production
observability approval, or a deployment configuration; Vercel deployment
remains a separate gated decision.
