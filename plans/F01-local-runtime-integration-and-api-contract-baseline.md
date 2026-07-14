# ExecPlan: F01 Local Runtime Integration and API Contract Baseline

**Phase:** `F01 - Local Runtime Integration and API Contract Baseline`
**Class:** Technical foundation
**Status:** Phase passed (`Continue`)
**Decision owner:** Primary agent
**Validation lane:** `V00` remains `WAITING_HUMAN` / `Revise`; `V01` is locked.

## Objective

Establish one reproducible local API-and-web development runtime with a
mechanically checked, role-neutral health contract and an accessible unavailable
service experience. F01 integrates only the existing technical shells. It does
not introduce product, learner, role, evidence, or readiness behavior.

## Verified Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| F00 passes | `plans/F00-repository-quality-foundation.md`, controller state, and inventory | Met |
| Reusable role-neutral scope | F01 roadmap amendment plus architecture and roadmap-gate reviews | Met |
| Existing health API and static web shell remain verified | F00 tests and execution record | Met |
| No external V00 evidence is required | Parallel-lane rule in `specs/roadmap.md` | Met |

## Scope

F01 is limited to `/health/live`, `/health/ready`, and `/openapi.json`, plus the
development-only process and web integration required to exercise that boundary.
The web may report API process availability; it must not describe configuration,
product, learner, mastery, evidence, or readiness state.

The phase is divided into independently verifiable slices:

1. `F01-01` — commit a canonical FastAPI-generated health OpenAPI artifact and
   add a deterministic, non-mutating contract-drift gate.
2. `F01-02` — derive a dependency-free TypeScript health response runtime
   validator from the canonical OpenAPI contract.
3. `F01-03` — validate a server-only API location and add a replaceable
   server-side health adapter.
4. `F01-04` — add accessible available, unavailable, and invalid-response web
   states using the server-side adapter.
5. `F01-05` — add a cross-platform development process supervisor with visible
   failure propagation and clean child-process shutdown.
6. `F01-06` — add the identical local/CI cross-process smoke command, record
   resource observations, and execute the full F01 exit gate.

Only one slice may be implemented and gate-reviewed per invocation.

## F01-01 Design

The backend Pydantic response model and FastAPI application factory remain the
only schema owners. A package module creates the app with explicit test settings,
calls `app.openapi()`, and refuses to export unless the generated path set is
exactly `/health/live` and `/health/ready`. It serializes the complete generated
document as sorted, indented UTF-8 JSON with LF endings and one final newline.

The `write` action intentionally regenerates the tracked artifact. The `check`
action performs a byte comparison, never writes, and returns a deterministic
nonzero exit for a missing, stale, malformed, or line-ending-drifted artifact.
Local documentation and CI invoke the same locked Python module command from
`apps/api`.

Explicit health operation identifiers are part of the contract so an internal
handler rename cannot silently rename a future generated client operation.

## F01-02 Design

The verified OpenAPI artifact remains the only consumer-schema input. A second
dependency-free Python generator resolves both health operations' successful
JSON response references, requires one shared local component, and derives a
strict TypeScript type plus runtime type guard from that component.

The generator supports only the current bounded OpenAPI 3.1 schema subset:
object components, unique required property names, string properties, and
optional string constants. It rejects every unimplemented semantic keyword,
explicit `additionalProperties`, divergent or external references, unsupported
types, and invalid identifiers. This fail-closed boundary prevents a generated
file from silently becoming stricter or looser than the authoritative schema.

The generated validator requires own required properties, does not coerce, and
accepts extra properties because the source schema does not prohibit them. It
contains no URL, environment access, fetch, React, state classification, or
network behavior. A later server adapter will own those concerns.

As in F01-01, `write` intentionally regenerates the tracked file while `check`
compares deterministic UTF-8/LF bytes without mutation. CI and local development
invoke the same locked command from `apps/api`.

## F01-03 Design

The API-location and adapter modules both begin with Next.js's compiler-enforced
`server-only` marker. `AI_PLATFORM_API_BASE_URL` is read only inside the marked
configuration module and is never exposed through `NEXT_PUBLIC_*`. Absence uses
`http://127.0.0.1:8000`; an explicit value must already be a canonical absolute
HTTP origin with an explicit port, literal `127.0.0.1` or `[::1]` host, and no
credentials, path beyond `/`, query, or fragment. A typed, value-redacting
configuration error is raised before fetch for every invalid explicit value.

The health adapter receives a branded origin, injected fetch implementation, and
caller-selected positive bounded timeout. It forms only `/health/live`, sends no
credentials, rejects redirects, opts out of caching, requires exact status 200
and `application/json`, parses JSON as untrusted input, and delegates response
acceptance to the generated `isHealthResponse` guard. It returns only an
available, unavailable, or invalid-response classification with safe reason
codes. It never returns or logs raw bodies, health details, status codes, URLs,
or exceptions. No runtime timeout default is selected in F01-03; F01-04 must
choose and record a provisional local UI deadline without treating it as a
performance gate.

Vitest aliases only the compile-time `server-only` marker to an empty local stub
so the actual production modules can be unit tested. Next production builds keep
the real marker. No runtime dependency or lockfile change is introduced.

## F01-04 Design

The home route becomes an explicitly dynamic async Server Component so API
availability is resolved once per server request, never queried during the
production build, and never frozen into static output. A new `server-only`
runtime resolver constructs the accepted F01-03 adapter from the validated API
origin, `globalThis.fetch`, and a provisional 2,000 ms deadline. The deadline is
one attempt with no retry; it is a local operational safety bound, not a latency
budget, SLA, or F01 performance gate.

Only the adapter result `kind` crosses into presentation. Configuration errors
and unexpected defects propagate through Next's route-error handling instead of
being disguised as API unavailability. The presentational shell renders exactly
three exhaustive, role-neutral states: local API available, local API
unavailable, and local API response invalid. It never receives or renders reason
codes, URLs, environment names, response details, status codes, bodies, or
exceptions. Copy states that the signal is local liveness only and makes no
product, learner, mastery, or readiness claim.

The status surface uses a labelled semantic section, visible state text,
`role="status"`, `aria-atomic="true"`, and an `aria-hidden` decorative marker.
Meaning does not rely on color. There is no client component, hydration state,
browser fetch, polling, retry, loading state, motion, or refresh control.

## F01-05 Design

One dependency-free Python 3.13 supervisor under the API package's development
namespace owns the local API and web development processes through a small root
entrypoint. The documented repository-root command runs the stdlib-only parent,
then launches locked `uv run` for the API and the pinned Next.js CLI for the web
with argument arrays, inherited stdio, `shell=False`, fixed literal-loopback
hosts, API port 8000, and web port 3000. The web child receives the server-only
API origin through `AI_PLATFORM_API_BASE_URL`. There is no arbitrary command,
host, origin, dynamic-port, daemon, or reload option.

Each service receives an isolated process group. On POSIX the supervisor sends
group SIGINT, then bounded SIGTERM and SIGKILL escalation. On Windows it sends a
targeted CTRL_BREAK event. Each Windows child is created suspended, assigned by
its retained process handle to a per-service kill-on-close Job Object, and only
then resumed; after the grace window the supervisor terminates that owned job.
Shutdown requests are bounded; a second operator signal skips the remaining
grace window. Native child output stays visible. Messages say only that
processes launched; F01-05 performs no readiness or HTTP probe.

If either process cannot start or exits unexpectedly, the supervisor identifies
the service and exit status, stops every owned sibling tree, and returns nonzero.
Unexpected exit zero maps to supervisor exit 1; ordinary child codes 1 through
125 are preserved. Clean operator shutdown returns zero only after cleanup.
No process is discovered or terminated by image name, port, or workspace scan.

## F01-06 Design

One repository-root command, `uv run --project apps/api --locked python
scripts/smoke.py`, is the complete local and CI cross-process smoke surface. A
thin root entrypoint loads a dependency-free API development module that reuses
F01-05 service construction, launch, signal, owned-tree, and shutdown primitives.
There is no second lifecycle implementation and no YAML-managed background
process.

The smoke uses literal `127.0.0.1` connections through `http.client`, without
DNS, proxies, redirects, credentials, or arbitrary destinations. It enforces a
45-second shared startup deadline, 100 ms polling, 5-second requests, and a 1
MiB body limit. Connection, reset, timeout, and HTTP protocol failures are
retryable only while the API liveness or web listener is starting. A received
wrong status, media type, JSON document, health contract, OpenAPI document, or
HTML contract fails immediately.

Success requires exact live and configuration-only ready payloads, parsed
runtime OpenAPI equality with the F01-01 canonical artifact, and an accessible
server-rendered available state that contains the local-liveness disclaimer but
no unavailable/invalid state, origin, environment name, path, or response
detail. Every post-launch path performs bounded owned-tree cleanup and waits for
ports 8000 and 3000 to close. Exit zero is possible only after assertions and
cleanup both succeed. Linux CI additionally records `/proc` process-group count
and resident bytes; unsupported host observations are explicit nulls, not a
false zero.

## Slice Non-Goals

- A handwritten consumer DTO, general client SDK, or domain schema.
- Client component, browser fetch, polling, retry, loading interaction, or
  browser-exposed URL in F01-04.
- HTTP health/OpenAPI assertions, readiness waits, restart policy, API reload,
  cross-process smoke command, or CI smoke step in F01-05.
- Browser automation, visual-regression claims, load budgets, production
  monitoring, deployment behavior, or readiness inference in F01-06.
- CORS, production routing, service discovery, deployment, or containers.
- Root process supervision, lifecycle handling, or cross-process smoke in
  F01-01 or F01-02.
- Database, ORM, migrations, identity, jobs, object storage, telemetry backend,
  LLM access, SSE, or persistence.
- Target, role, competency, learner, curriculum, tutoring, assessment, mastery,
  evidence, simulation, or readiness state.
- Any change to V00 evidence, V01 eligibility, or later validation phases.

## Test and CI Strategy

`F01-01` tests prove exact health scope, equality with runtime FastAPI generation,
stable explicit operation identifiers, Pydantic component references, repeated
byte identity, LF normalization, write behavior, non-mutating missing/stale/CRLF
failure behavior, committed-artifact parity, and CLI exit semantics. The complete
affected API format, lint, strict-type, test, branch-coverage, and 95% line gates
must pass. CI runs the exact documented locked drift command before API tests.

Later slices add server configuration, web, lifecycle, and cross-process tests.
No later-slice test can be counted toward `F01-01` completion before its behavior
exists.

`F01-02` Python tests prove source-contract verification, exact response-reference
traversal, deterministic TypeScript generation, unsupported-schema failures,
non-mutating write/check semantics, and CLI exit codes. Vitest exercises the
generated guard against valid responses, allowed extras and empty detail, null,
arrays, inherited-only or missing properties, primitive mismatches, and constant
mismatch. The complete affected API and web quality/build gates must pass with
the API absent.

`F01-03` tests cover absent and canonical loopback configuration, normalization
and unsafe-destination rejection, redacted configuration errors, environment
read timing, pre-fetch failure, exact request options and path, injected fetch,
bounded timeout, network and non-200 failure, media type, malformed JSON,
generated-contract rejection, accepted extra properties, server-only markers,
and absence of client-public configuration. The complete web lint, strict type,
test, and API-absent build gates plus both generated-contract checks must pass.

`F01-04` tests table-cover every adapter classification and prove kind-only
mapping, exact runtime timeout wiring, request-time environment reading, typed
configuration failure before fetch, all three rendered states, semantic status
markup, text-independent color meaning, and absence of internal values in HTML.
The route must remain server-only and explicitly dynamic. The complete web lint,
strict type, test, and API-absent build gates plus both generated-contract checks
must pass; the build must report `/` as dynamic and browser assets must contain
no API configuration, origin, or health path.

`F01-05` tests exact fixed commands, working directories, environment updates,
inherited stdio, Windows and POSIX process-group launch flags, start failure,
unexpected zero and nonzero exits, sibling cleanup, exit-code mapping, signal
handling, graceful deadlines, forced escalation, and safe output. Real helper
parent/grandchild trees exercise graceful, stubborn, and leader-exited cleanup
on the host OS; the same tests are included in the existing Ubuntu API test lane
without adding an F01-06 smoke step. Full API format, lint, strict type, test,
branch-coverage, canonical-contract, repository diff, and line-ending gates must
pass.

`F01-06` tests bounded literal-loopback HTTP behavior, exact health/OpenAPI/web
assertions, response confidentiality, startup-only retries, fixed deadlines,
child and launch failures, interruption, cleanup and port-closure failures,
Linux group-scoped resource parsing, CLI exits, and local/CI command parity. The
same exact root command runs locally and in a separate Ubuntu job after both
quality jobs. F01 cannot pass from workflow configuration alone: a successful
GitHub Actions run for the exact intended revision is required.

## Performance, Storage, and Cost

F01-01 adds no dependency, process, service, network call, learner data, or
persistent runtime storage. Record generation/check duration and artifact bytes.
There is no external API or model cost. Later slices must record startup,
shutdown, smoke time, and process-resource deltas before the F01 phase gate.

F01-02 likewise adds no dependency, process, network call, or persistent runtime
storage. Record generator/check duration, generated bytes, and production build
impact. No runtime latency or external API cost is claimed before an adapter
exists.

F01-03 adds one potential loopback request only when a future server caller uses
the adapter. It adds no dependency, process, persistent storage, migration,
external API, model call, or client bundle import. The timeout is a required
operational bound supplied by the future caller, not an observed performance
budget. The locked install took 32.2 seconds, the API-absent build took 8.3
seconds, the production config/adapter/environment-example sources total 4,787
bytes, and no API-origin or health-path string appears in the built client or app
route output because no UI imports the adapter. Real API latency and process
resources remain unmeasured until F01-06.

F01-04 performs one bounded loopback request per rendered page request and adds
no retry. The API-absent path may add up to 2,000 ms before server output. It adds
no dependency, persistent storage, migration, external API, model call, browser
request, or client JavaScript. Record added production source bytes and build
duration; defer real API latency and process resources to F01-06.

The implementation adds 5,655 net production source bytes across the route,
runtime resolver, shell, and styles. The API-absent production build completes
in 8.7 seconds and reports `/` as dynamic; browser static assets total 629,565
bytes and contain no API environment name, origin, or health path. A real
production request with the API refusing connections returned the accessible
unavailable page in 179 ms. This is a local failure-path observation, not an API
latency budget.

F01-05 adds two long-lived development processes but no runtime dependency,
application storage, migration, external service, or model call. Record source
and test bytes, locked-install impact, time until both TCP listeners accept,
aggregate owned-process working set, graceful shutdown duration, induced child
failure duration/status, forced helper-tree cleanup, transient cache effects, and
whether Linux execution remains unverified. HTTP bodies and smoke timing remain
F01-06 evidence.

The repaired Windows lifecycle observation reached both listeners in 1,215 ms,
used 370,302,976 aggregate owned-process working-set bytes, and completed clean
`Ctrl+C` shutdown in 370 ms with no owned PID or listener remaining. An induced
API bind failure propagated exit 1 in 1,057 ms, stopped the owned web tree, and
left the unrelated blocker alive. Graceful and stubborn helper parent/grandchild
trees plus a leader-exited/live-descendant tree all cleaned up. Production
supervisor sources total 27,546 bytes, lifecycle tests and fixtures total 30,822
bytes, and the transient Next.js development output totals 12,053 bytes. Locked
synchronization changed no dependency or lockfile. These are local development
observations, not budgets; HTTP smoke latency and live Ubuntu execution remain
F01-06 evidence.

The final local Windows F01-06 smoke reached API liveness in 1,426 ms, completed
all HTTP assertions in 3,614 ms, and completed owned-tree shutdown in 204 ms.
Ports 3000 and 8000 were closed afterward. Its warm Next.js development cache
grew by 1,014 bytes; across local runs that ignored directory totals 16,359,470
bytes. The smoke production sources total 17,706 bytes and focused tests total
27,452 bytes. Windows process memory remains the F01-05 observed 370,302,976-byte
working set because the dependency-free `/proc` observer reports unsupported
host measurements as null. No application data, migration, external service,
model call, or additional dependency is introduced. The exact Ubuntu smoke
observed 4 owned processes and 714,330,112 resident bytes, reached API liveness
in 2,541 ms, completed in 6,359 ms, and shut down in 251 ms with both ports
closed. These are development-run observations, not production budgets.

## Acceptance Criteria

### F01-01 slice

1. The committed artifact is generated from the application factory and contains
   exactly the two health paths and generated `HealthResponse` schema.
2. Repeated generation is byte-identical, UTF-8, LF-only, and has one trailing
   newline under the locked toolchain.
3. Check mode succeeds for the committed artifact and fails without mutation for
   missing, stale, and CRLF-altered artifacts.
4. Local documentation and CI use the same locked command.
5. All affected F00 API quality gates still pass with at least 95% line coverage.
6. Independent review finds no handwritten parallel schema, forbidden runtime
   integration, domain behavior, or validation-lane change.

### F01-02 slice

1. The tracked TypeScript type and guard are generated only from the verified
   OpenAPI artifact and contain no handwritten response fields or literals.
2. Both health operations must resolve to the same supported local component;
   unsupported or newly constrained schema features fail closed before writing.
3. Repeated generation is byte-identical, UTF-8, LF-only, and has one trailing
   newline; check mode detects missing, stale, and CRLF output without mutation.
4. The runtime guard accepts exactly the current schema semantics, including
   allowed extra properties, and rejects nonconforming unknown values without
   coercion or sensitive-value logging.
5. Local documentation and CI use the same locked check command; all affected
   API and web quality gates and the API-absent production build pass.
6. Independent review finds no dependency, handwritten DTO, networking,
   configuration, UI, domain behavior, or validation-lane change.

### F01-03 slice

1. API configuration is server-only, non-public, canonical, explicitly ported,
   loopback-only, and fails with a typed redacted error before networking.
2. The replaceable adapter can request only `GET /health/live`, omits credentials,
   rejects redirects, disables caching, and applies a caller-supplied bounded
   timeout.
3. Exact 200 JSON is validated only through the generated runtime guard; all
   network, status, media, parse, and contract failures are safely classified
   without leaking body, detail, status, URL, or exception data.
4. Focused configuration and adapter tests plus every affected web and generated
   contract gate pass without the API running.
5. No dependency, lockfile, UI, browser fetch, CORS, process supervisor, domain
   behavior, or validation-lane change is introduced.
6. Independent review accepts behavior, portability, test sufficiency, scope,
   and controller disposition.

### F01-04 slice

1. The home route resolves health at request time through the accepted server
   adapter and never calls the API during an API-absent production build.
2. A documented 2,000 ms one-attempt deadline bounds the server request without
   being presented as a performance guarantee.
3. Presentation receives only `available`, `unavailable`, or `invalid-response`;
   configuration and unexpected errors propagate rather than being reclassified.
4. Each state has distinct visible text in one labelled semantic status region;
   meaning does not depend on color and no internal or sensitive value renders.
5. No dependency, client component, browser fetch, CORS, retry, polling, process
   supervisor, domain behavior, or validation-lane change is introduced.
6. Focused and complete affected gates pass, and independent review accepts
   accessibility, confidentiality, runtime wiring, build behavior, and scope.

### F01-05 slice

1. One documented repository-root command starts the fixed API and web
   development processes with literal-loopback bindings and visible native logs.
2. No shell interpolation, arbitrary process target, reload, readiness probe,
   retry/restart, detached ownership, or production-management behavior exists.
3. Startup failure or either unexpected child exit is visible, stops every owned
   sibling tree, and produces the documented nonzero exit status.
4. SIGINT/SIGTERM cleanup is bounded and process-tree aware on Windows and POSIX;
   stubborn owned descendants receive deterministic forced escalation.
5. Host helper-tree tests and an actual Windows root-command lifecycle run prove
   no owned PID or listener remains; Ubuntu execution is configured honestly and
   is not claimed until CI runs.
6. Full affected gates and independent review accept lifecycle, portability,
   failure propagation, ownership safety, resource evidence, and scope.

### F01-06 slice

1. Local documentation and a dedicated supported-Linux CI job run the same
   no-argument locked repository-root command.
2. Startup and every request are bounded; responses are size-limited; only
   transient connection failures are retried during listener startup.
3. Exact health, canonical OpenAPI, accessible available-page, and server-only
   confidentiality assertions pass against live API and web processes.
4. Every post-launch outcome cleans the owned process trees; success also proves
   both fixed ports closed, while failure returns a safe nonzero status.
5. Focused tests provide at least 95% line and branch coverage for the smoke
   policy and the complete local F00/F01 quality and runtime gates pass.
6. Independent review accepts scope and evidence; F01 remains externally blocked
   until this exact revision succeeds in the Ubuntu CI smoke job.

### F01 phase

The complete exit gate remains the one in `specs/roadmap.md`: clean cross-platform
process lifecycle, server-only configuration, offline web build, contract-derived
bounded health validation, accessible failure states, deterministic smoke parity,
all F00 gates, recorded resource deltas, and independent scope verification.

## Failure Handling

- Contract mismatch or absence fails with regeneration guidance and no mutation.
- Unexpected API paths fail export/check rather than silently expanding F01.
- A quality or portability failure returns the slice to `Revise`.
- Invalid F01-03 configuration throws before fetch; runtime request failures are
  classified without logging or returning untrusted details.
- F01-04 lets typed configuration and unexpected errors fail the server request;
  it does not conceal them in an availability state.
- F01-05 treats launch/group-control/cleanup failure as visible supervisor
  failure, stops any process already owned, and never falls back to name- or
  port-based termination.
- F01-06 treats contract, deadline, process, interruption, cleanup, resource,
  or lingering-port failures as nonzero; it never logs response bodies or
  private exception details and never converts unsupported resource data to zero.
- A need for browser-direct routing, domain state, a deployment decision, or V00
  bypass narrows or stops the phase instead of broadening it.

## Rollback Strategy

For F01-01, remove the generator, artifact, tests, operation IDs, documentation,
and CI drift step together. No dependency, data, schema migration, service, or
external state must be rolled back. Later slices must extend this section before
introducing their behavior.

For F01-02, remove its generator, generated TypeScript module, focused Python and
Vitest tests, documentation, and CI check together. No package lock, data,
service, migration, or external state requires rollback.

For F01-03, remove the API-base module, health adapter, environment example,
Vitest marker alias/stub, focused tests, and documentation together. No package
lock, data, service, migration, process, or external state requires rollback.

For F01-04, restore the static page and shell and remove its runtime resolver,
focused UI/runtime tests, styles, and documentation together. No dependency,
lockfile, data, migration, service, or external state requires rollback.

For F01-05, remove the development supervisor, helper-tree fixture, lifecycle
tests, mypy scope updates, and documentation together. No dependency, lockfile,
application data, migration, service, or external state requires rollback.

For F01-06, remove the smoke module and root entrypoint, focused tests,
documentation, and dedicated CI job together. No dependency, lockfile,
application data, migration, service, or external state requires rollback;
transient ignored Next.js development cache can be regenerated by later local
development.

## Progress and Decisions

- `2026-07-12`: F01 was formally defined and independently accepted as the
  earliest eligible role-neutral foundation phase.
- `2026-07-12`: F01-01 entry conditions and design were independently reviewed.
  The accepted design exports the complete factory-generated OpenAPI document,
  guards the exact health path set, compares canonical bytes, adds no dependency,
  and defers every consumer, web, process, and smoke behavior.
- `2026-07-12`: F01-01 implementation passes locked synchronization, lock
  validation, formatting, linting, strict typing, 15 API tests, and the 95%
  coverage gate. Total API coverage is 98%; the contract module has 100% line
  and branch coverage. Two checks and two independent writes produced identical
  1,861-byte artifacts in about 0.58-0.59 seconds each. Missing and drifted
  targets returned exit 1 without mutation.
- `2026-07-12`: Independent verification reproduced the canonical equality,
  exact path scope, operation IDs, byte/line-ending behavior, CLI failures,
  focused and complete API gates, CI/local parity, prospective diff, and V00
  protection. It found no code or scope defect. Its only controller finding was
  the expected interim inventory hash, which was refreshed during finalization.
  F01-01 is accepted; F01 remains in progress with no phase gate decision.
- `2026-07-12`: The controller's exact next action was narrower than the older
  F01 slice list, which had bundled API-location validation into F01-02. Under
  the governing precedence, architecture and roadmap review narrowed F01-02 to
  the generated runtime validator only and moved server-only API location to
  F01-03. The accepted design adds no schema/runtime dependency and rejects all
  unsupported OpenAPI semantics rather than approximating them.
- `2026-07-12`: F01-02 implementation generates an 822-byte TypeScript type and
  guard directly from both health response references. The generator and its 30
  focused tests reach 100% line and branch coverage; the full API suite passes
  45 tests at 99% coverage. The generated guard passes 3 focused and 4 total web
  tests, and the static production build completes in 7.9 seconds. Two checks
  and two writes are byte-identical at about 0.64-0.67 seconds each. Missing,
  stale, CRLF, and invalid-source cases fail without target mutation. No package
  or lockfile changed.
- `2026-07-12`: Independent verification reproduced the 822-byte generated
  output, schema traversal and derivation, fail-closed keywords and references,
  own-property and extra-property semantics, non-mutating failure behavior,
  command parity, portability, and forbidden-scope scan. It found no code or
  semantic defect. Its only findings were the expected interim F01 plan and
  inventory hashes, which were refreshed during finalization. F01-02 is accepted;
  F01 remains in progress with no phase gate decision.
- `2026-07-13`: Architecture and roadmap review kept F01-03 server-only and
  local-only, required canonical literal loopback origins and visible redacted
  configuration failure, preserved the generated guard as response authority,
  and deferred UI, timeout selection, process lifecycle, and smoke orchestration.
  The 52 focused and 56 full web tests, lint, strict typecheck, two canonical
  checks, 40 focused API contract tests, locked install, and API-absent build all
  pass. No dependency or lockfile changed. Independent verification reproduced
  the configuration and adapter boundaries, tests, portability, confidentiality,
  dependency history, prospective diff, and lane protection and found no code or
  scope defect. Its stale controller and test-count findings were repaired during
  finalization. F01-03 is accepted; F01 remains in progress with no phase gate.
- `2026-07-13`: Architecture and roadmap reviews accepted an explicitly dynamic
  server route, kind-only presentation, a provisional 2,000 ms one-attempt bound,
  and propagation of configuration errors. F01-04 implements the three semantic
  text states with no client behavior. Nineteen focused and 74 full web tests,
  lint, strict typecheck, both canonical contract checks, the 8.7-second
  API-absent dynamic build, a real unavailable production render, client-asset
  confidentiality scan, and 1440-by-1000 visual inspection pass. Independent
  verification reproduced 19 focused tests, lint, typecheck, dynamic-build
  evidence, asset confidentiality, accessibility, kind-only mapping, timeout
  wiring, visual hierarchy, dependency history, and lane protection and found no
  code or scope defect. Its stale-checkpoint finding was repaired during
  finalization. F01-04 is accepted; F01 remains in progress with no phase gate.
- `2026-07-13`: Architecture and roadmap reviews accepted a dependency-free
  root supervisor with fixed loopback commands, inherited native logs, isolated
  process groups, bounded cleanup, and exact failure propagation while deferring
  readiness and smoke to F01-06. A first live design put `uv run` outside the
  supervisor and Windows returned `0xC000013A` despite complete cleanup; moving
  locked `uv run` into the owned API child repaired the signal boundary. A later
  ownership probe showed a dead Windows group leader could hide a descendant;
  suspended launch plus pre-resume Job Object assignment repaired that defect.
  Thirty-seven focused tests at 96% supervisor coverage, 82 full API tests at
  97% total coverage, real Windows lifecycle and failure evidence, locked sync,
  format, lint, strict typing, and both canonical checks pass. Independent
  verification reproduced 37 focused tests, format, lint, strict typing,
  ownership safety, resource bytes, clean process state, empty index, and V00
  protection and found no material defect. F01-05 is accepted; F01 remains in
  progress with no phase gate decision.
- `2026-07-13`: The later implementation-loop attachment authorized the already
  defined and independently reviewed F01. F01-06 added one exact local/CI root
  smoke command, reused F01-05 ownership and signals, and added bounded health,
  canonical OpenAPI, accessible web, confidentiality, resource, cleanup, and
  closed-port assertions. Independent review found and the parent repaired raw
  cache-observation diagnostics and incomplete shared-deadline enforcement.
  Forty-four focused tests at 98% smoke coverage, 126 full API tests at 97%, all
  affected quality/contract gates, and a live Windows smoke pass. F01 remains
  externally blocked until the exact intended revision succeeds on Ubuntu CI.
- `2026-07-14`: Pushed revision
  `25994d214ed5b39d4b6c73ba0e075b10ee4a5a66` reached Ubuntu CI, where API
  quality failed before tests because Linux typeshed omits the Windows-only
  `ctypes.WinDLL` and `ctypes.get_last_error` attributes named directly by the
  supervisor. The retryable repair moves both behind one typed, runtime-checked
  private adapter, preserves native last-error values, and adds delegation,
  unavailability, and error-provenance regressions. Native, Linux-targeted, and
  Windows-targeted strict mypy pass all 23 files; 82 focused tests and 127 full
  API tests pass at 97% total coverage; a real Windows smoke still leaves both
  ports closed. F01 remains `Revise` until the repaired exact revision passes
  Ubuntu API, web, lifecycle, runtime-smoke, and resource gates.
- `2026-07-14`: Pushed revision
  `34fe4465e567a562f22b7c63bd6d5df29fdef09a` repaired Linux mypy. Exact
  GitHub Actions run `29359471181` passed API synchronization, both canonical
  contract checks, Ruff, strict mypy, and all 127 API tests in 2.05 seconds, then
  failed the 95% coverage gate at 92% total and 84% supervisor because the
  Windows Job Object and suspended-thread helpers were unexercised on Ubuntu.
  Web quality passed 6 files and 74 tests; runtime smoke was skipped by the
  failed API dependency. Cross-platform fake-kernel success and failure tests
  now execute those production helpers without exclusions: 47 focused tests
  pass in 17.79 seconds and 136 full API tests pass in 18.96 seconds at 99%
  supervisor and total coverage. Read-only review accepted this behavior-driven
  matrix while retaining real Windows lifecycle coverage. The user authorized
  Codex to commit and push bounded verified repairs and to use the exact pushed
  revision's Actions run as the gate. F01 remains `Revise` pending that run.
- `2026-07-14`: Exact revision
  `2bc6dfa392725ea725dda6915a7d6ab68a246251` completed GitHub Actions run
  `29363263721` successfully on Ubuntu 24.04. API quality passed both canonical
  contracts, Ruff, strict mypy, repository line endings, and 136 tests in 2.18
  seconds at 99% total and supervisor coverage. Web quality passed lint, strict
  typecheck, 74 tests in 1.22 seconds, and the dynamic production build, which
  compiled in 3.6 seconds. The identical runtime smoke reached API liveness in
  2,541 ms, observed 4 owned processes and 714,330,112 resident bytes, completed
  all assertions in 6,359 ms, shut down in 251 ms, and closed both ports.
  Independent review accepted the repair and constitutional scope. F01 passes
  its phase exit gate with `Continue`; V00 remains `WAITING_HUMAN / Revise`,
  V01 remains locked, and no next phase starts in this invocation.

## Phase Gate Decision

**Gate decision:** `Continue`. F01 passes as a role-neutral local runtime and API
contract foundation. The decision is limited to the named F01 contract and exact
revision evidence above; it is not role, learner, mastery, readiness, deployment,
or beta evidence and does not satisfy any V00 condition.

## Gate Decision Rules

- **Continue:** the current slice passes every listed criterion and independent
  verification; checkpoint F01 as still in progress.
- **Revise:** contract, test, reproducibility, CI parity, or portability fails.
- **Narrow:** implementation would require a broader client or network boundary.
- **Stop:** the phase would constrain role selection or bypass validation.
