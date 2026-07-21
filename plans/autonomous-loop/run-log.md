# Autonomous Loop Run Log

## Run 1 — 2026-07-12

Initialized the durable V00 controller and drafted the pending-approval symmetric demand-sampling protocol plus unsent privacy-safe practitioner, recruitment, and cost request templates. Validation and independent re-review passed; gate remains `Revise`; status is `WAITING_HUMAN` for the sampling-sufficiency, practitioner-qualification, and cost-boundary decisions.

## Run 2 — 2026-07-12

Added the separately gated, role-neutral F00 lane and implemented the locked
FastAPI/Next.js repository foundation, tests, CI, and line-ending policy. Local
API, runtime, web, build, and production-dependency checks passed; independent
review findings were repaired. F00 gate is `Continue` / `PHASE_PASSED`; V00 stays
`WAITING_HUMAN` / `Revise`, V01 stays locked, and no product capability was added.

## Run 3 — 2026-07-12

Defined and independently verified `F01 - Local Runtime Integration and API
Contract Baseline` as a health/OpenAPI-only foundation phase. Updated the
inventory and controller; F01 remains `NOT_STARTED` with no runtime files or
tests. V00 remains `WAITING_HUMAN` / `Revise`, V01 remains locked, and the next
run is limited to the `F01-01` health-contract export and drift-gate slice.

## Run 4 — 2026-07-13

Created the F01 ExecPlan and implemented only F01-01: a canonical FastAPI-generated
health OpenAPI artifact, explicit operation IDs, a deterministic non-mutating
write/check module, 10 focused tests, documentation, and identical CI/local drift
validation. The full API suite passed 15 tests at 98% coverage; the contract
module reached 100% line and branch coverage. Independent verification accepted
the slice with no code or scope defect. F01 remains `IN_PROGRESS` with no phase
gate decision; V00 remains `WAITING_HUMAN` / `Revise`, V01 remains locked, and the
next run is limited to the F01-02 contract-derived health runtime validator.

## Run 5 — 2026-07-13

Reconciled F01-02 to validator-only scope and generated an 822-byte TypeScript
health response type guard directly from the verified OpenAPI artifact, with a
fail-closed dependency-free Python generator, deterministic write/check command,
30 focused Python tests, and 3 focused Vitest cases. The full API suite passed 45
tests at 99% coverage, both contract generators reached 100% line/branch coverage,
the 4-test web suite and static production build passed, and independent review
found no code or scope defect. F01 remains `IN_PROGRESS` with no phase gate;
V00 remains `WAITING_HUMAN` / `Revise`, V01 remains locked, and the next run is
limited to F01-03 server-only API-base configuration and health adapter work.

## Run 6 — 2026-07-13

Implemented only F01-03: canonical server-only literal-loopback API-origin
configuration with typed redacted pre-fetch failure, plus an injected-fetch,
bounded, non-cached and redirect-rejecting `/health/live` adapter that validates
exact 200 JSON through the generated guard and exposes only safe classifications.
Locked install, 52 focused and 56 full web tests, lint, strict typecheck, both
canonical checks, 40 focused API contract tests, and the API-absent 8.3-second
build passed. Independent verification found no code or scope defect after two
bookkeeping repairs. F01 remains `IN_PROGRESS` with no phase gate; V00 remains
`WAITING_HUMAN` / `Revise`, V01 remains locked, and only F01-04 accessible health
states are eligible next.

## Run 7 — 2026-07-13

Implemented only F01-04: an explicitly dynamic server route, a server-only
runtime resolver with a provisional 2,000 ms one-attempt bound, and a restrained
accessible surface for local API available, unavailable, and invalid-response
states. Presentation receives only the result kind; configuration and unexpected
errors propagate. Locked install, 19 focused and 74 full web tests, lint, strict
typecheck, both canonical checks, the API-absent 8.7-second dynamic build, a real
179 ms unavailable render, browser-asset confidentiality scan, contrast checks,
and visual inspection passed. Independent verification found no code or scope
defect. F01 remains `IN_PROGRESS` with no phase gate; V00 remains
`WAITING_HUMAN` / `Revise`, V01 remains locked, and only F01-05 process
supervision is eligible next.

## Run 8 — 2026-07-13

Implemented only F01-05: one fixed repository-root development supervisor for
the locked API and pinned Next.js CLI, with literal-loopback commands, inherited
logs, visible failure propagation, POSIX process groups, and Windows children
created suspended and assigned to kill-on-close Job Objects before resuming.
Thirty-seven focused and 82 full API tests pass at 96% supervisor and 97% total
coverage; all affected API quality and canonical checks pass. Actual Windows
startup, clean shutdown, induced child failure, graceful/forced helper trees,
and leader-exited descendant cleanup leave no owned PID or listener and preserve
an unrelated blocker. Independent verification found no material defect. F01
remains `IN_PROGRESS` with no phase gate; V00 remains `WAITING_HUMAN` / `Revise`,
V01 remains locked, and only F01-06 smoke and exit-gate work is eligible next.

## Run 9 — 2026-07-13

Independent verification identified that the exact governing attachment
authorizes F00 only and explicitly forbids F01. Removed only Run 9's F01-06
smoke, focused tests, documentation, and CI additions and restored the pre-run
F01-05 files. Preserved the pre-existing uncommitted F01-01 through F01-05 work
because deleting it also requires user direction. F00 remains `PHASE_PASSED /
Continue`; V00 remains `WAITING_HUMAN / Revise`; V01 remains locked. The
controller disposition is `Stop` until the user decides whether the pre-existing
F01 work should be retained and explicitly authorized or rolled back. No commit
or push occurred.

## Run 10 — 2026-07-13

Reconciled the later implementation-loop attachment as the governing
authorization for the formally defined and reviewed F01, then implemented only
F01-06. Added one exact local/CI root smoke command that reuses F01-05 process
ownership and signals, bounds loopback requests and startup, verifies exact
health/OpenAPI/accessible-web contracts, records resources, and requires cleanup
plus closed ports. Independent review found two bounded-observation defects;
cache diagnostics and shared-deadline enforcement were repaired with four
regressions. Forty-four focused and 126 full API tests pass at 98% smoke and 97%
total coverage; all affected gates and the live Windows smoke pass. F01 remains
`WAITING_EXTERNAL`, V00 remains `WAITING_HUMAN / Revise`, and V01 stays locked.
No commit or push occurred; exact-revision Ubuntu CI remains required.

## Run 11 — 2026-07-14

Pushed revision `25994d214ed5b39d4b6c73ba0e075b10ee4a5a66`
reached Ubuntu CI, but API quality failed at strict mypy because Linux typeshed
does not expose Windows-only `ctypes.WinDLL` or `ctypes.get_last_error`. Replaced
the ten direct references with one typed, runtime-checked private adapter and
added delegation, explicit-unavailability, and preserved-errno regressions.
Native, Linux-targeted, and Windows-targeted strict mypy pass all 23 files; 82
focused and 127 full API tests pass at 97% total coverage; locked sync, Ruff,
both canonical contract checks, and a real Windows smoke pass with 204 ms
shutdown and closed ports. Independent verification found no code, scope,
secret, or constitutional defect. F01 is `FAILED_RETRYABLE / Revise` until the
repair is committed, pushed, and passes exact-revision Ubuntu API, web,
runtime-smoke, and resource gates. V00 remains `WAITING_HUMAN / Revise`; V01
remains locked. No commit or push occurred. The pre-existing tracked 66,312,302
byte archive remains untouched and is recorded as a repository/CI cost risk.

## Run 12 — 2026-07-14

Pushed revision `34fe4465e567a562f22b7c63bd6d5df29fdef09a`
repaired Linux strict mypy. Exact GitHub Actions run `29359471181` then passed
API synchronization, both contracts, Ruff, strict mypy, and all 127 API tests in
2.05 seconds, but failed the 95% coverage gate at 92% total and 84% supervisor;
the Windows Job Object and suspended-thread helpers had no cross-platform test
execution. Web quality passed 6 files and 74 tests, while runtime smoke was
skipped by the API dependency. Added behavior-driven fake-kernel success and
failure coverage for both helpers, including structure configuration, process
assignment, thread selection, error provenance, and handle cleanup. Forty-seven
focused tests pass in 17.79 seconds and 136 full API tests pass in 18.96 seconds
at 99% supervisor and total coverage without exclusions; native and Linux mypy
and focused Ruff also pass. A read-only reviewer accepted the matrix as the
smallest meaningful repair and retained real Windows lifecycle tests. The user
gave Codex standing authorization to commit and push bounded verified repairs
on this branch and use each exact GitHub Actions run as the gated review. Commit
`2bc6dfa392725ea725dda6915a7d6ab68a246251` then completed exact run
`29363263721` successfully: API passed 136 Linux tests in 2.18 seconds at 99%
coverage; web passed 74 tests and the production build; runtime smoke observed 4
owned processes and 714,330,112 resident bytes, reached API liveness in 2,541
ms, completed in 6,359 ms, shut down in 251 ms, and closed both ports. F01 is
`PHASE_PASSED / Continue`. V00 remains `WAITING_HUMAN / Revise`, V01 remains
locked, and no next phase started in this invocation.

## Run 13 — 2026-07-14

Recomputed both lanes after F01 passage. V00 remains `WAITING_HUMAN / Revise`,
V01 and every later validation phase remain locked, and no defined phase was
eligible. Architecture review compared PostgreSQL/migrations with correlation
and confidential diagnostics; it selected the latter as the smaller reversible
boundary because it reuses the F01 health transaction without an external
service, persistent metadata, provisional migration tooling, exporter, or
backend. Roadmap-gate review required an amendment-only invocation. Added the
narrow F02 roadmap contract and `NOT_STARTED` ExecPlan, updated inventory and
controller records, and added no executable, dependency, lockfile, workflow,
test, product, learner, domain, analytics, audit, privacy-approval, or V17A
behavior. JSON/controller/hash/scope/diff checks pass. Independent final
verification returned `ACCEPT` with no actionable finding. Exact GitHub Actions
verification of the pushed amendment remains the publication gate; F02-01 may
begin only on a later invocation after entry conditions are revalidated.

## Run 14 — 2026-07-15

Exact F02-definition revision `6de13bba593e4b7aae30f112feb4a22a106ef7e2`
passed GitHub Actions run `29367566575`: API quality passed synchronization,
contract, Ruff, strict-mypy, 136-test, and 99%-coverage gates; web quality passed
74 tests and the production build; runtime smoke passed process, resource,
health, cleanup, and port-closure gates. The user then delegated standing
decision ownership to Codex so the loop does not pause for user review. Updated
only controller and inventory records: Codex now selects and accepts the next
eligible technical/controller action, preregisters and applies internally
decidable V00 rules, and stages, commits, and pushes bounded verified work. V00
is reclassified from `WAITING_HUMAN` to `WAITING_EXTERNAL / Revise`; no external
evidence is treated as supplied, V01 remains locked, and the next eligible
implementation slice remains F02-01 on a later invocation.

The user's GitHub deployment idea is recorded as a maturity objective: GitHub
owns source, CI, environment governance, and deployment orchestration, while
GitHub Pages is rejected as a runtime target for the FastAPI plus server-rendered
Next.js architecture. A real containerized managed-PaaS environment remains a
separately gated future phase because provider, region, credentials, isolation,
rollback, and the exact Next.js mode are provisional. This authority amendment
changes no source, dependency, lockfile, workflow, test, schema, runtime, or
evidence artifact. Independent final verification returned `ACCEPT` with no
actionable finding. The exact pushed revision's GitHub Actions run remains the
publication gate.

## Run 15 — 2026-07-15

Revalidated F02 entry on exact-CI-accepted revision
`a35e1908f2d37dfcc2932d69bfd24a7bbd55dffd` and implemented only F02-01.
Selected exact OpenTelemetry API/SDK pins and an app-local provider with no
processor, exporter, global registration, backend, persistence, or egress. Added
strict W3C `traceparent` handling, safe roots, a pure-ASGI liveness boundary,
one fixed allowlisted completion event, confidential generic process logging,
disabled Uvicorn access logging, provider lifecycle ownership, and adversarial
tests. The health response and generated API/web contracts remain unchanged.

Independent verification found that the first draft privately rejected reserved
v00 flag bits and that invalid environment configuration escaped Uvicorn import
as a raw Pydantic traceback containing the supplied value. Reserved flags and
future versions now delegate to the official propagator. The entrypoint now
emits only a fixed generic error and exits nonzero; a real subprocess regression
proves the canary, traceback, and validation input are absent. Fifty focused
diagnostic tests and 186 full API tests pass at 99% coverage. Locked sync/lock,
both contracts, Ruff, native/Linux/Windows strict mypy, and the Windows runtime
smoke pass. Dependency, event-byte, latency, install, failure, upgrade, rollback,
and zero-egress/storage/model-cost observations are recorded in the F02 plan and
checkpoint.

The user reports connecting the repository to Vercel. Official Vercel material
now supports FastAPI Python Functions and combined Next.js/FastAPI Services, so
Vercel replaces GitHub Pages as the provisional deployment candidate while
GitHub remains source, CI, and exact-revision acceptance. No deployment config
or local link exists, the Vercel surfaces have beta/runtime constraints, and a
later gated phase must reconcile the function topology with the approved
container-managed-PaaS constitution. F02 remains deployment-neutral.

Independent final rereview reproduced the complete local gate, canary,
structure, scope, and confidentiality evidence and returned `ACCEPT` with no
actionable finding. Implementation revision
`1cd879ef9a37dc04a28c09e7fed23d40441fdb3c` then completed exact GitHub Actions
run `29372599433` successfully in 1 minute 28 seconds. API quality job
`87219074832` passed locked synchronization, both canonical contracts, Ruff,
strict mypy, line endings, and all 186 tests in 3.00 seconds at 99% coverage.
Web quality job `87219074897` passed lint, strict typecheck, all 74 tests in 1.32
seconds, and the production build with zero npm vulnerabilities. Runtime-smoke
job `87219208633` observed API liveness in 2,633 ms, four owned processes,
716,132,352 aggregate resident bytes, 16,368,938 Next.js build bytes, total smoke
in 6,213 ms, shutdown in 251 ms, and closed both ports.

F02-01 is accepted. F02 remains `IN_PROGRESS` with a null phase decision because
F02-02, F02-03, and the complete exit gate are absent. Global controller state
returns to `READY`, with F02-02 eligible only on a later invocation. V00 remains
`WAITING_EXTERNAL / Revise`, V01 remains locked, and no V00 evidence, deployment
configuration, or F02-02 work was added in this invocation.

## Run 16 - 2026-07-15 (started)

Revalidated the F02-02 entry gate from clean synchronized revision
`7ac1fb3c938472a8c803e1ee98a772b42f92cdb8`, whose controller publication passed
exact GitHub Actions run `29373234548` across API, web, and runtime-smoke jobs.
Started only `F02-02 - Server-to-server propagation`. V00 remains
`WAITING_EXTERNAL / Revise`, V01 remains locked, F02 retains a null phase gate,
and F02-03 plus Vercel deployment configuration remain outside this invocation.

Implemented one server-only client span around the existing bounded health
adapter with exact `@opentelemetry/api@1.9.1`, `core@2.9.0`, and
`sdk-trace@2.9.0` pins. The app-local provider has no global registration,
processor, exporter, context manager, backend, persistence, or egress. It starts
from explicit root context, injects one official canonical nonzero W3C
`traceparent`, and emits one frozen allowlisted web completion event. The F01
timeout, abort, cache, credential, redirect, status, media-type, contract, and
public UI-result behavior remains unchanged. A production build gate now scans
browser assets for fixed diagnostic and API-configuration markers.

Independent review found and the parent repaired four material defects: the
first base provider read ambient `OTEL_*` configuration; default setup could
fail at module evaluation instead of returning the frozen no-op boundary; the
adapter fallback validator did not reject zero identifiers; and the first
browser marker used the wrong API environment name. The final lower-level
provider ignores hostile SDK-disable, always-off sampler, service, and resource
values under an executable regression. A valid 200 response-detail canary is
accepted but absent from the event. The optional OpenTelemetry API peer shared
with Next.js is documented as a future global-registration risk.

All 61 focused web tests and all 97 tests in 8 files pass, as do lint, strict
typecheck, a clean production build, and the browser confidentiality scan over
10 assets and 629,565 bytes. The scan failed nonzero for a temporary banned
marker and passed again after removal. Clean install completed in 66,659 ms and
the audit found zero vulnerabilities. Five installed OpenTelemetry directories
contain 14,822,615 bytes; manifest/lock growth is 240/2,697 bytes. A 500-call
observation emitted exactly 500 260-byte events; local baseline p50/p95/max was
0.049/0.120/2.463 ms and instrumented was 0.095/0.210/0.709 ms. These are
observations, not budgets; API/model/telemetry egress and storage cost remain
zero.

The unaffected API gate passes locked sync/lock, both contracts, Ruff,
native/Linux/Windows strict mypy, and 186 tests at 99% coverage. The final
Windows smoke reached API liveness in 1,936 ms, completed in 4,031 ms, shut down
in 155 ms, and closed both ports. Its logs observed matching web/API trace IDs
with distinct spans; F02-03 still owns the automated real-process correlation,
rendered-output confidentiality, resource, Ubuntu, and complete phase-exit
assertions.

Independent final verification returned `ACCEPT` with no actionable finding.
F02-02 is `IMPLEMENTED_UNVERIFIED` until its exact pushed API, web, and runtime
GitHub Actions jobs pass. The controller moves to `WAITING_EXTERNAL` for that
machine gate only; no user review is pending. F02-03, the F02 phase decision,
V00/V01 changes, and Vercel deployment remain excluded.

Implementation revision `b6550c58f4342a82197455f53eb064a32306e8fc`
then completed exact GitHub Actions run `29400137315` successfully in 1 minute
33 seconds. API quality job `87302552878` passed locked synchronization, both
contracts, Ruff, strict mypy across 26 files, line endings, and 186 tests in
2.45 seconds at 99% coverage. Web quality job `87302552907` passed locked
install with zero vulnerabilities, lint, strict typecheck, all 97 tests in 8
files in 2.13 seconds, and the production build; compile completed in 3.6
seconds and the confidentiality gate scanned 10 browser files totaling 629,565
bytes. The Ubuntu fixed observation emitted exactly 500 260-byte events;
baseline p50/p95/max was 0.045/0.115/4.392 ms and instrumented was
0.088/0.229/7.106 ms.

Runtime-smoke job `87302713249` reached API liveness in 1,924 ms, observed four
owned processes and 747,077,632 aggregate resident bytes, produced 17,013,419
Next.js bytes, completed in 4,773 ms, shut down in 252 ms, and closed both
ports. Its logs showed a matching validated trace ID across the web and API
events with distinct spans. F02-02 is accepted. F02 remains `IN_PROGRESS` with
a null phase gate because F02-03 and the complete exit gate remain absent. The
controller returns to `READY`, with F02-03 eligible only on a later invocation.
V00 remains `WAITING_EXTERNAL / Revise`, V01 remains locked, and no deployment
configuration was added.

## Run 17 - 2026-07-16 (started)

Revalidated the F02-03 entry gate from clean synchronized revision
`4957e42c66d192fb53463a392eb7ccf4399d7ae5`, whose F02-02 controller
publication passed exact GitHub Actions run `29401670748`. Started only
`F02-03 - Runtime proof`. V00 remains `WAITING_EXTERNAL / Revise`, V01 remains
locked, F02 retains a null phase gate, and Vercel deployment remains outside
this invocation.

Extended the unchanged root smoke command with an isolated private runtime proof.
It validates 24 API and 24 web exact-schema events, 21 correlated request pairs,
W3C parent relationships, safe roots, distinct spans, explicit absent and
malformed context, and 20 measured requests whose first four overlap at a
barrier. Ephemeral downstream servers prove available, unavailable, and invalid
response classification. Bounded child stderr, browser response bodies, and
headers are scanned for diagnostic or trace leakage. Cancellation, timeout,
induced shutdown, capture overflow, descendant cleanup, process reaping, and
port closure are covered without changing supervisor behavior, public schemas,
web runtime behavior, dependencies, lockfiles, workflows, or deployment.

Independent verification found seven concrete lifecycle, confidentiality,
concurrency, header, schema, and capture-bound defects; all were repaired and
regression tested. A second verifier pass was unavailable because the agent
quota was exhausted, so the controller performed the required read-only fallback
diff audit and repaired one additional launch-to-capture interruption race.

The focused runtime suite passes 102 tests. The complete API suite passes 244
tests in 13.38 seconds with 97% branch-aware coverage (`smoke.py` 95%,
supervisor 99%). Both contract checks, locked synchronization, Ruff, native,
Linux-targeted, and Win32-targeted strict mypy, all 97 web tests, lint,
typecheck, production build, and browser confidentiality checks passed during
local development. The final Windows root smoke observed 48 events, 21
correlations, four overlapping requests, 4,128 ms total smoke, 51 ms shutdown,
and closed both ports. Locked sync, both contract gates, Ruff, and native,
Linux-targeted, and Win32-targeted mypy were repeated and passed against the
exact publication diff.

F02-03 remains `IMPLEMENTED_UNVERIFIED` and the controller moves to
`WAITING_EXTERNAL` for the exact pushed API, web, and runtime-smoke GitHub
Actions jobs only. No user review is pending. F02 cannot pass and no deployment
work can begin until that machine gate is accepted.
Exact implementation revision `82736aff83c0c4fce66b31095b65fdc7e57d1c5f`
then reached GitHub Actions run `29509035888`. API job `87657348971` passed
locked synchronization, contracts, Ruff, strict mypy, line endings, and 244
tests in 3.67 seconds at 97% coverage. Web job `87657349046` passed a
zero-vulnerability install, lint, typecheck, all 97 tests in 2.14 seconds,
production build, and the 10-file 629,565-byte browser confidentiality scan.
Runtime-smoke job `87657590869` failed after the private scenario succeeded
because its outer full-stderr scan detected an Ubuntu-only forbidden raw value.
The value remained suppressed, so the Actions log exposed no confidential child
content.

The controller disposition is `Revise`. A fixed non-secret taxonomy now reports
only the rejected class (`raw_url`, `raw_health_path`, raw header class, or
`raw_exception`) while continuing to reject and suppress the value. That change
passes 108 focused tests, 250 full API tests in 11.75 seconds at 97% coverage,
Ruff, native/Linux/Win32 mypy, and a 4,269 ms Windows root smoke with 48 events,
21 correlations, 51 ms shutdown, and closed ports. F02 remains `IN_PROGRESS`
with a null gate pending the next exact pushed runtime result.
Classifier revision `16bf84c9919ccf16d1e06e1542245737bd61cde4` then
passed exact GitHub Actions run `29510082305`. Initial API job `87660936291`
passed contracts, Ruff, strict mypy, line endings, and 250 tests in 3.93 seconds
at 97% coverage. Initial web job `87660936295` passed zero-vulnerability install,
lint, typecheck, all 97 tests in 2.11 seconds, production build, and the 10-file,
629,565-byte browser scan. Initial runtime job `87661156124` passed with 48
events, 21 correlations, four processes, 841,670,656 resident bytes, 1,928 ms API
liveness, 5,012 ms smoke, 403 ms shutdown, and closed ports.

Because the preceding behavior-equivalent revision had failed once, the
controller reran the full dependent chain twice. Runtime jobs `87661534645` and
`87661831197` also passed. Across all three successful Ubuntu attempts, resident
memory was 841,670,656-844,980,224 bytes, API liveness 1,832-2,340 ms, smoke
5,012-7,554 ms, and shutdown 50-403 ms; event, correlation, concurrency, process,
byte-bound, and port-closure assertions stayed exact.

The earlier raw-marker source remains unknown and is recorded as a residual
flake risk. Its value never entered Actions logs, and any recurrence now reports
only a fixed safe category while remaining rejected. F02 is accepted as
`PHASE_PASSED / Continue`. V00 remains `WAITING_EXTERNAL / Revise`, V01 stays
locked, deployment remains deferred, and this invocation stops before another
phase.

## Run 18 - 2026-07-16 (definition completed)

First confirmed that F02 controller revision
`8963101805d6f29f4701c91764b5563f07ff07c8` passed exact GitHub Actions run
`29511515229`. API job `87665879457` passed 250 tests at 97% coverage; web
job `87665879508` passed 97 tests, its production build, zero-vulnerability
audit, and the 10-file 629,565-byte browser confidentiality scan; runtime-smoke
job `87666108627` passed with 48 events, 21 correlations, four workers, four
owned processes, bounded resources, clean shutdown, and closed ports.

Recomputed both lanes from that accepted boundary. The controlled V00 inbox
still contains no evidence file, so V00 remains `WAITING_EXTERNAL / Revise` and
V01 stays locked. No human review is pending. The foundation lane had no
approved phase after F02, so the governing controller required a narrow roadmap
amendment before any further implementation.

Parallel read-only architecture and roadmap reviews agreed on a portable,
role-neutral container baseline and no deployment in this invocation. Their
scope recommendations differed: architecture proposed both images in the first
slice, while roadmap review identified the API artifact as the smallest safe
unit. The controller selected
`F03 - Portable Container Runtime and Non-Production Preview Baseline`, with
F03-01 limited to the FastAPI OCI artifact, F03-02 reserved for the web/private
binding topology, and F03-03 reserved for one exact-revision Vercel preview.

Official Vercel Services, container, binding, and pricing documentation inspected
on 2026-07-16 supports a plausible OCI/private-service preview while the
capabilities remain Beta. F03 therefore preserves provider-neutral images, keeps
the API private, leaves the current loopback parser unchanged until F03-02, and
does not approve Vercel for production.

This invocation changes only the roadmap, the F03 ExecPlan, and controller
records. It adds no source, dependency, lockfile, workflow, Dockerfile,
deployment configuration, migration, or secret; it does not intentionally
invoke a deployment. The reported Vercel Git integration may auto-create an
unverified preview on push. That provider side effect is not F03 evidence and
cannot advance F03-03. F03 remains `NOT_STARTED`; F03-01 is eligible only on a
later invocation after this definition amendment passes its exact publication
gate.

Independent verification returned `Revise` on two documentation-only findings:
the first draft categorically denied a remote deployment even though the reported
pre-existing Git integration may auto-create a preview on push, and two inventory
sentences still described this amendment as a repair. The records now distinguish
no intentional deployment from an unverified provider side effect, explicitly
exclude that side effect from F03/F03-03 evidence, and use amendment wording. The
verifier otherwise confirmed the exact F02 run evidence, phase boundaries,
protected V00 state, hashes, JSON, line endings, file whitelist, loopback/API
privacy constraints, and official provider claims.
## Run 19 - 2026-07-16 (F03 implementation started)

Reanchored the autonomous loop to the latest durable pull request #1 steering
and GitHub issue #2. Verified clean synchronized head
`5b19455034583da0d0ec40c82edf70423b93b2df`; its run `29514959237` passed only
API quality (`87677547747`), Web quality (`87677547757`), and Runtime smoke
(`87677707977`). That three-check revision is an entry boundary, not F03
acceptance. V00 remains `WAITING_EXTERNAL / Revise`; V01 remains locked.

Read-only architecture and roadmap specialists both found that the local
container/Vercel F03 contradicted issue #2 and that issue #3 reserves deployment
for later F04. Replaced the obsolete definition with `F03 - GitHub Phase-Gate
Control Plane`. The integrated design derives dependencies only from the
roadmap, uses versioned status/blocker/claim policy, rejects cross-lane effects,
validates exact checked-out Git HEAD and authoritative hashes, and emits a
bounded deterministic projection only after full repository validation.

Implemented the standard-library controller, root CLI, adversarial-test surface,
exact-head checkout for every workflow job, and exact `Phase gate` plus final
`Gate projection` jobs. The projection revalidates the repository, waits for all
four upstream jobs with `always()`, and fails on pending, failed, cancelled, or
skipped results. Workflow permissions remain read-only, actions remain pinned,
checkout credentials are not persisted, and no secrets, artifact trust,
repository mutation, product runtime, persistence, LLM, deployment, or Vercel
configuration is added.

Local validation then passed. The hardened adversarial controller suite passed
133 tests in 8.91 seconds, and the full API suite passed 383 tests in 23.59
seconds at 97% branch-aware coverage. Locked sync, both generated-contract
checks, Ruff, and native/Linux/Win32 strict mypy across 30 files passed. The web
gate completed in 43.854 seconds: locked install audited 385 packages with zero
vulnerabilities; lint, strict typecheck, all 97 tests in 8 files, the production
build, and the 10-file/629,565-byte browser confidentiality scan passed. The
real runtime smoke completed in 4.591 seconds with 48 events, 21 correlations, 4
concurrent requests, 1,386 ms API liveness, 3,874 ms internal smoke, 51 ms
shutdown, and closed ports.

Independent verification found and drove repairs for unknown explicit roadmap
dependency IDs, hard-coded upstream-result sources, coordinated V00 blocker
reclassification, incomplete transition evidence, ignored nontechnical
foundation blockers, dirty-worktree SHA labeling, invalid claim prerequisites,
and controller workflow bypasses. Its final rerun reproduced 133 targeted and
383 full API tests, 97% branch-aware coverage, Ruff, strict mypy, authoritative
hashes, JSON, and diff checks with no open material finding.

The hardened CLI rejects the dirty pre-commit worktree with
`worktree_not_exact_head`, so clean exact-head Phase gate and Gate projection
commands are intentionally deferred until the implementation commit exists. A
pre-hardening 20-iteration observation averaged 173.578 ms, peaked at 1,392,192
traced Python heap bytes, and emitted an 853-byte deterministic projection; the
clean exact-commit duration will be refreshed after commit. The first sandboxed
`npm ci` was denied with `spawn EPERM`; the required escalated run passed and is
recorded as an environment-permission observation. No dependency or lockfile
changed. Independent verification is accepted; the implementation revision and
the separate acceptance-state revision must still pass their own exact five
GitHub checks. No chat approval is required for any repair or acceptance step.

### F03 exact implementation attempt 1 - failed closed and repaired

Pushed implementation attempt `9746ceb16a3bbfc1e95a8bfadae6224fe77dfe21`.
Its clean local Phase gate and Gate projection were eligible, but exact GitHub
Actions run `29521143904` was not accepted: Web quality job `87698239481`
succeeded; API quality `87698239491`, Phase gate `87698239511`, and Gate
projection `87698419129` failed; Runtime smoke `87698419979` was skipped.

The Phase gate emitted `state_hash_mismatch`, and API reproduced the mismatch in
32 controller tests. The authoritative state had hashed raw bytes from a clean
Windows worktree where two tracked V00 Markdown files were transparently CRLF-
converted; the exact Linux checkout used LF Git blobs. The repair canonicalizes
CRLF to LF before hashing authoritative text and adds an LF/CRLF checkout
regression. It preserves clean-worktree enforcement and exact-SHA validation.
The repaired local suite passes 134 targeted tests in 10.06 seconds and 384 full
API tests in 27.15 seconds at 97% branch-aware coverage; the complete repair API
gate took 31.902 seconds. Ruff, strict mypy, and contract drift checks pass.
Web/runtime executables were unchanged, so their already-recorded successful
local gates remain applicable. Follow-up verification and a new exact five-check
implementation revision remain mandatory; failed run `29521143904` is repair
evidence only.

### F03 canonical-LF repair independently verified

The follow-up `verification_reviewer` accepted the bounded eight-file repair.
It reproduced LF checkout success, CRLF checkout success, and rejection of a
real content mutation with `state_hash_mismatch`. The targeted controller suite
passed 134 tests in 9.43 seconds; the full API suite passed 384 tests in 26.50
seconds at 97% branch-aware coverage overall and for the controller. Ruff,
native/Linux/Win32 strict mypy, both generated-contract checks, all 24 canonical
hashes, JSON, line-ending, final-newline, and diff checks passed. No material
finding remains.

F03 remains `IMPLEMENTED_UNVERIFIED`. The repair must be committed and pass all
five exact GitHub jobs before a separate acceptance-state revision may be
created; that revision must then pass its own five exact jobs.

### F03 exact implementation attempt 2 - runtime smoke failed closed

Pushed canonical-hash repair revision
`34d5de2b5af15ec39e09b0f91ed5d358020dcfed`. Exact run `29523254781`
rejected it: API quality job `87705173886`, Web quality job `87705173871`,
and Phase gate job `87705173912` succeeded; Runtime smoke job
`87705355479` failed; Gate projection job `87705481759` failed closed.

The Runtime smoke log reported forbidden category `raw_url`. Linux Next.js had
nondeterministically written a loopback or documentation URL as framework-owned
stderr. The accepted F02 validator correctly rejected the raw value because it
scans every captured byte; the first proposed repair weakened that rule by
scanning only proof-bearing lines, and independent verification returned
`REVISE`. The corrected repair restores the full-capture validator unchanged.
Real API and web stderr is routed before capture: structured JSON, inner-proof,
and diagnostic-marker candidates are forwarded byte-exact; confidential
canaries, oversized lines, I/O failures, and premature pipe closure fail safely;
ordinary framework-owned lines become fixed allowlisted `process.log` events.

The runtime suite now passes 126 adversarial tests in 0.74 seconds. Two real
local smokes pass in about 7 seconds each with 48 events, 21 correlations, 4
concurrent requests, 12,638 diagnostic bytes, and 14,223-14,224 captured bytes;
shutdown completed in 51-102 ms and both ports closed. The complete API suite
passes 402 tests in 26.69 seconds at 97% overall branch-aware coverage with
`smoke.py` at 95%. The 134 controller tests, Ruff, native/Linux/Win32 strict
mypy across 30 files, both contracts, canonical hashes, JSON, and diff checks
pass. Corrected independent follow-up verification then returned `ACCEPT`
with no material finding. It reproduced 126 runtime tests in 1.32 seconds, 47
supervisor tests in 16.27 seconds, 134 controller tests in 9.03 seconds, and 402
full API tests in 27.84 seconds at 97% overall coverage with `smoke.py` at
95%. Ruff, native/Linux/Win32 mypy, both contracts, 24 hashes, final newlines,
diff checks, and two real smokes also passed. Run `29523254781` remains repair
evidence only; a new exact five-check implementation revision is required.

### F03 exact implementation attempt 3 - accepted on both exact-head runs

Pushed the accepted pre-capture runtime-log repair as implementation revision
`fe49b609767e27d52fae999c229502ed98866dff`. Two exact-head GitHub Actions runs
completed against that exact SHA: push run `29528587173` and pull-request run
`29528587169`. All five required jobs succeeded in both runs: API quality
(`87723081841` / `87723082409`), Web quality (`87723081644` / `87723082444`),
Runtime smoke (`87723264188` / `87723243300`), Phase gate (`87723082122` /
`87723082447`), and Gate projection (`87723443710` / `87723382365`) — ten job
executions total, all `success`. This satisfies the implementation-side exit
condition of the F03 acceptance sequence: a repaired implementation revision
passing all five exact-head checks.

### F03 acceptance-state revision published

This revision updates the F03 ExecPlan, autonomous state, checkpoint, run log,
and implementation inventory to record implementation revision
`fe49b609767e27d52fae999c229502ed98866dff`'s exact five-job success and sets
F03 to `PASSED / Continue`. No application, controller, or workflow code
changed; only documentation and state/inventory records were updated, so the
previously reproduced local API, web, runtime, and controller evidence for the
unchanged implementation remains applicable. The controller-policy schema,
hash, and consistency rules were re-validated locally against the updated
`state.json` and `implementation-inventory.json` before this revision was
committed. This acceptance-state revision's own exact five-job GitHub run is
now required and will be recorded as durable pull request #1 evidence once
observed. A successful implementation SHA does not automatically accept this
later state-update SHA.

### F04 defined; definition revision passed exact-head CI

Formally defined F04 in specs/roadmap.md and
plans/F04-vercel-deployment-baseline.md, recording the topology decision
required by GitHub issue #3: specs/tech-stack.md approves containers on a
managed PaaS as the backend runtime (binding; only the vendor is
Provisional), so F04 selects Option 2 -- Vercel hosts only the Next.js web
tier. Verified directly (gh secret list, GitHub check-runs, commit-status
queries) that no Vercel secret or connected project existed before this
phase. Added a matching IN_PROGRESS F04 inventory entry, positioned
immediately after F03 to satisfy the phase-gate validator's positional
roadmap-inventory pairing.

Definition revision `001b0eeb1faa3939057732fd80a0bafa635bddc7` was pushed and
opened as pull request #5. Its exact five required checks passed via
pull-request run `29596684247`: API quality `87938687679`, Phase gate
`87938687704`, Web quality `87938687741`, Runtime smoke `87938871665`, Gate
projection `87939008145` -- all success. This confirms the definition is
internally consistent; it is not F04 acceptance. A real Vercel account and
project (`web`, scoped to apps/web) now exist locally via the Vercel CLI
(.vercel/ and .env.local confirmed git-ignored). Connecting Vercel's GitHub
Git integration failed with "You need to add a Login Connection to your
GitHub account first" -- a browser OAuth action only the account owner can
complete, recorded as F04's next blocking dependency.

### Vercel Git integration connected; first real deployment blocked

The user authorized the GitHub Login Connection and ran `vercel git connect`
successfully, verified via the Vercel REST API (`link.type=github`,
`link.repo=ai-learning-platform`). Found and fixed the project's
`rootDirectory` (was `.`, corrected to `apps/web`) via the Vercel API.
Pushed revision `b37bfc130ce3f436c32eb8b5481142c378fca68b`, which triggered
the first real, GitHub-linked deployment (`dpl_7hovy7BzNQBC7vG9MVZBbyAzBdAw`)
-- but it reported `readyState: BLOCKED` and a `failure` commit status
("Deployment was blocked"). Diagnosed the likely cause: the commit's author
email (`mahmoud.bayoumi@valeo.com`, from this machine's global git config,
never set by the executor) does not match the email verified on the
`TheBayoumi` GitHub/Vercel account, matching Vercel's documented
committer-association block. The user reports this is now fixed; this
revision retriggers a fresh deployment attempt to confirm.

### Real deployment succeeded; health-status surface verified

The blocked deployment's actual cause was confirmed by GitHub itself:
"GitHub couldn't verify an account for the commit" -- neither the work email
nor the user's personal Gmail address were verified on the `TheBayoumi`
GitHub account. Switched the local (repo-scoped only) git identity to
GitHub's guaranteed noreply address
(`107598562+TheBayoumi@users.noreply.github.com`), amended and
force-pushed the affected unmerged commit (`f5206e2` -> `787534a`, content
unchanged, confirmed via `git diff`). The resulting deployment
`dpl_F4HfP5AL5Nv4KPnqGYbLhrWQ71U5` reached `readyState=READY`
(target=preview, region=iad1); GitHub commit status `success` ("Deployment
has completed"). The user visually confirmed (browser access bypasses
Vercel's Deployment Protection SSO wall, which blocked the executor's own
fetch attempts) that the deployed page renders the F01/F02 health-status
surface showing API unavailable/offline, the correct and expected behavior
since this web-tier-only deployment has no API origin configured.

## Run 25 - 2026-07-21 (F04 closure repair: state and controller reconciliation)

Reverified the clean live starting state before writing. Branch
`automation/f04-vercel-deployment-baseline` was synchronized at exact SHA
`ca08301b46e49945a805f20a07866a931a8e81e0`; pull request #5 was open,
mergeable, and ahead of `main`. GitHub Actions run `29616557723` passed API
quality, Web quality, Runtime smoke, Phase gate, and Gate projection on that
exact SHA. GitHub deployment `5496257300` and Vercel deployment
`dpl_64G3A2Zim5iWcQ2YzrQnW9runPii` reported successful/`READY` preview state
for the same revision. The Vercel project remained `web`, project ID
`prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN`, Root Directory `apps/web`, Node.js `24.x`,
with no production deployment observed.

The live audit rejected the earlier `PASSED` conclusion. The controller
projected passed F04 as `DEFINE_F04 / F04`; `future_phase_boundary` called F04
eligible after F03; goal, checkpoint, and inventory Markdown still described
F03 acceptance as pending; repository metadata named the obsolete
`automation/v00-phase-loop` branch and predecessor SHA; and the workflow push
filter also named that obsolete branch. All 134 existing phase-gate tests passed
while preserving that self-loop, proving a regression-suite blind spot.

The deployment evidence also failed F04's own exit contract. `vercel rollback`
returned HTTP 422 because a preview had never served production traffic. A
rejected production rollback command and continued reachability of two preview
URLs do not move traffic. Unauthenticated requests followed Vercel Deployment
Protection redirects to a login page that returned HTTP 200. An authenticated
`vercel curl` diagnostic reached the exact deployment and rendered the expected
API-unavailable state with accessible `role=status` semantics, but no committed
exact-SHA verifier exists. Version-controlled Vercel configuration, compatible
Vercel npm installation, deployed confidentiality proof, required resource/cost
measurements, and the tracked 66,312,302-byte archive also remain unresolved.

Read-only mission, roadmap, architecture, and controller reviewers independently
returned `Revise` and confirmed the same evidence defects. They also confirmed
that the repair remains role-neutral, V00 remains `WAITING_EXTERNAL / Revise`,
V01 remains locked, and no readiness or validation claim is introduced.

This bounded repair returns F04 to `FAILED_RETRYABLE / Revise`, derives the
active lane frontier and foundation successor from roadmap/inventory state,
represents no defined successor explicitly, generalizes controller transition
blockers and automation-branch matching, clarifies the traffic-reversion gate,
and synchronizes authoritative records. It does not change an alias, deploy an
API, promote production, remove the archive, define F05, merge the PR, or close
issue #3.

Local affected validation passed before publication. The controller suite passed
137 tests, including active-frontier, nullable-successor, valid-successor start,
failed-entry and empty-entry waits, failed-entry transition rejection,
branch-pattern, and
post-F04 boundary regressions. API canonical generation, Ruff format/lint, strict
mypy, and the full suite passed: 405 tests, 97% total line coverage, and 96%
coverage for `phase_gate.py`. Web `npm ci`, lint, strict typecheck, 97 tests, the
Next.js production build, and the 629,565-byte browser confidentiality scan
passed. The local machine used Node 25.2.1 and npm 11.18.0; Node remains inside
the manifest's supported range but differs from `.nvmrc` 24.18.0 and the Vercel
project setting 24.x, so this is an observation rather than reproducibility
evidence.

The first runtime-smoke attempt after the production build failed closed on an
unexpected diagnostic-event count. Its public wrapper intentionally suppressed
the raw child evidence, so no exact cause can be claimed. A bounded direct-child
rerun then produced exactly 24 API and 24 web events with the required
classifications, and the public runtime smoke passed with 48 events, 21
correlations, four concurrent requests, 12,639 diagnostic bytes, 14,224 captured
bytes, API live in 1,416 ms, total smoke in 4,724 ms, and 51 ms shutdown. No smoke
code was changed for the non-reproduced observation. Dirty-worktree phase-gate
validation failed closed as designed with `worktree_not_exact_head`; clean-head
proof is deferred to the published exact revision.

Independent post-change verification, publication of the implementation
revision, and its exact GitHub/Vercel results are recorded in the durable pull
request evidence after they complete. F04 remains `Revise`; the only next
eligible action is a supported non-production verification-alias reversion with
exact served-SHA proof and restoration of the intended final target.

The first independent post-change review returned `Revise` because a newly
defined, entry-ready `F05 / NOT_STARTED` frontier fell through to a repair action;
the earlier successor unit test had bypassed repository validation. The repair
now records failed entry conditions explicitly, projects an entry-ready frontier
as `START_FOUNDATION_PHASE`, projects a failed entry as a non-eligible wait, and
uses an end-to-end synthetic-roadmap/inventory/state regression. The same review
also tightened the formal F04 exit gate to repeat build reproducibility,
measurement/cost, and archive-hygiene requirements. Focused independent rereview
then found that a failed non-transition entry could coexist with the exact
implementation-transition tuple and still project acceptance, while an empty
entry list could start vacuously. Transition readiness now rejects any failed
entry, start readiness requires declared entry conditions, and validated
regressions prove both paths fail closed. Final focused rereview returned
`ACCEPT` with no material findings after independently passing all 137 controller
tests, Ruff, strict mypy, authoritative hash/state validation (bypassing only the
intentional dirty-worktree guard), and `git diff --check`. Publication evidence
remains pending; the review accepts this bounded repair, not F04 itself.

## Run 26 - 2026-07-21 (F04 non-production alias traffic reversion)

Reverified the authoritative clean starting state before mutation. Repository
`TheBayoumi/ai-learning-platform` was on branch
`automation/f04-vercel-deployment-baseline` at exact SHA
`ceaf60d2ce5adf826b8268c32e513569a35eeb0c`; pull request #5 was open and
mergeable. Exact push run `29829521304` and pull-request run `29829523486` each
passed API quality, Web quality, Runtime smoke, Phase gate, and Gate projection.
GitHub's Vercel status was successful for `READY` preview
`dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z` at the same SHA. The Vercel project still
used project ID `prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN`, team ID
`team_bZWPrEPMa4sBoWU7syo3ZIRZ`, Root Directory `apps/web`, GitHub repository
`TheBayoumi/ai-learning-platform`, and production branch `main`.

Selected two distinct immutable `READY` previews from the same project and F04
branch. Prior A was `dpl_64G3A2Zim5iWcQ2YzrQnW9runPii` at exact SHA
`ca08301b46e49945a805f20a07866a931a8e81e0`, created
`2026-07-17T22:00:51.867Z` and ready `2026-07-17T22:01:11.519Z`. Intended final
B was `dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z` at exact SHA
`ceaf60d2ce5adf826b8268c32e513569a35eeb0c`, created
`2026-07-21T12:17:58.572Z` and ready `2026-07-21T12:18:18.445Z`. Both were
preview targets in `iad1`; GitHub confirmed both commits belong to the
repository and A is an ancestor of B.

Created only the new dedicated hostname
`f04-reversion-proof-web.vercel.app`. Using Vercel CLI 56.3.1's authenticated
`vercel api` wrapper over the supported
`POST /v2/deployments/{deployment-id}/aliases` endpoint, the same alias followed
the exact sequence B to A to B. Initial B assignment returned no prior target.
The backward move returned B as `oldDeploymentId`; final restoration returned A
as `oldDeploymentId`. Each bounded metadata observation converged in one
attempt within a declared 60,000 ms limit and 2,000 ms backoff, proved the alias
was present only on the target deployment, and mapped the target to its exact
expected SHA, project, `READY` state, and preview target.

After every control-plane verification, authenticated `vercel curl` requested
the proof hostname. Each request returned HTTP 200 application HTML with no
redirect, `role=status`, and the expected API-unavailable state. Bounded
assertions found no loopback API origin, `/health/live`, trace identifier, or
confidential diagnostic marker. Only content type, cache control, bounded body
size, and a response digest were retained; no full HTML, token, cookie, bypass
value, temporary share URL, raw authorization header, or CLI authentication
state entered the repository.

Before the proof, the only ordinary project alias was the Git-managed branch
alias on B. After final restoration, that exact mapping remained unchanged and
the dedicated proof alias pointed to B. No production alias existed before or
after, Root Directory and production branch remained unchanged, and the existing
errored production-target deployment still had no aliases. No production,
custom-domain, environment, Git-integration, protection, or project-setting
mutation was performed.

The machine-readable proof is
`plans/F04-vercel-alias-reversion-evidence.json`. The focused evidence contract
suite passed 21 tests: the valid proof, authoritative hash binding, and required
fail-closed cases for missing deployments, identical or stationary transitions,
non-READY or wrong-project deployments, missing or mismatched SHAs, stale
previous alias ownership, authentication redirects, HTTP without alias
verification, restoration to A, empty transitions, unbounded polling, and
committed credential/share material. Exact assertion and object-key allowlists
also reject incomplete response semantics, raw responses, and creator metadata.

Local validation passed before publication: all 21 focused evidence tests and
all 158 controller tests; canonical OpenAPI and TypeScript generation checks;
Ruff format and lint; strict mypy; and all 426 API tests at 97% total coverage.
Web clean install, lint, strict typecheck, all 97 tests, production build, and
the 629,565-byte browser confidentiality scan passed. The root runtime smoke
passed with 48 exact events, 21 correlations, four concurrent requests, bounded
diagnostics, and clean shutdown. Repository diff and secret checks found no
credential, temporary protected-preview access material, or unrelated file.

Independent final read-only review returned `ACCEPT` with no material findings.
It independently confirmed the live alias remained on B, A no longer held the
alias, both deployment/SHA chains were exact `READY` previews, ordinary and
production alias state remained isolated, protected HTTP returned the expected
application response, all 26 authoritative hashes agreed, and the complete
controller and API gates passed. Historical intermediate states remain
represented by the sanitized, hash-bound provider response record because only
the restored final alias state is live-queryable.

Only `f04.rollback_reversion` is removed. F04 remains
`FAILED_RETRYABLE / Revise` with `f04.deployed_page_verification`,
`f04.build_reproducibility`, `f04.resource_measurements`, and
`f04.repository_payload_hygiene`. V00 remains `WAITING_EXTERNAL / Revise`; V01
remains locked. This run stops after independent review, exact-head publication,
remote check verification, durable PR/issue evidence, and a final proof-alias
stability read. It does not implement another F04 blocker or create an
acceptance-state revision.
