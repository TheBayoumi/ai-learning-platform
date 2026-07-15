# ExecPlan: F02 Cross-Process Correlation and Confidential Diagnostics Baseline

**Phase:** `F02 - Cross-Process Correlation and Confidential Diagnostics Baseline`
**Class:** Technical foundation
**Status:** In progress - F02-01 accepted; F02-02 independently accepted locally
**Decision owner:** Primary agent
**Validation lane:** `V00` remains `WAITING_EXTERNAL` / `Revise`; `V01` is locked.

## Objective

Establish one vendor-neutral, confidentiality-bounded diagnostic path across the existing
Next.js server-to-FastAPI health transaction. F02 will correlate that technical
request with W3C Trace Context and OpenTelemetry-compatible span ownership while
restricting emitted diagnostics to a fixed allowlist. It does not add product
analytics, learner or domain identifiers, persistent telemetry, or an exporter.

## Verified Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| F00 and F01 pass | F00/F01 plans, controller state, inventory, and exact GitHub Actions evidence | Met |
| Telemetry standard is approved and backend remains replaceable | `specs/tech-stack.md` | Met |
| Scope is reusable for every plausible V00 candidate | Architecture review and the role-neutral F01 transaction | Met |
| No validation evidence is inferred or required | Parallel-lane rules in `specs/roadmap.md` | Met |

The phase definition is accepted separately from implementation. This ExecPlan,
the roadmap entry, and controller records do not start F02 or satisfy its exit
gate. A later invocation must recheck these entry conditions before F02-01.

## Why This Phase Is Next

F01 leaves one real cross-process transaction and a minimal JSON formatter that
can emit arbitrary message text, but it has no request correlation, context
isolation, safe event vocabulary, or confidentiality gate. Standard correlation
and fail-closed diagnostics are required regardless of the eventual Target and
can be exercised now without inventing product state.

PostgreSQL connectivity and migrations were considered and deferred. PostgreSQL
is approved, but driver and migration choices are provisional, an external
service would broaden local and CI lifecycle, and no approved V02 domain schema
exists to migrate. F02 therefore takes the smaller reversible diagnostic boundary.

## Scope and Slices

Only one slice may be implemented and gate-reviewed per invocation.

1. `F02-01 - API diagnostic context` (**accepted on exact pushed CI**): record the minimal instrumentation
   dependency/ownership decision; define a fixed safe event vocabulary; add W3C
   context validation, safe-root creation, API middleware/context isolation, and
   allowlisted JSON diagnostics; replace or suppress unsafe raw request/error
   logging; and prove malformed-input, canary-redaction, concurrency, cleanup,
   and exact-count behavior.
2. `F02-02 - Server-to-server propagation` (**independently accepted locally; exact-CI acceptance pending**): create and propagate context only
   inside the Next.js server around the existing health adapter; emit bounded
   safe outcome/timing events; preserve timeout, cache, redirect, credential,
   and result-classification behavior; and prove that no context or diagnostics
   enter browser assets, rendered output, or client state.
3. `F02-03 - Cross-process diagnostic gate`: exercise one real health request
   and induced failures through the existing runtime; prove matching trace IDs,
   distinct spans, confidentiality, concurrent isolation, cleanup, and bounded
   event volume; record dependency, startup, shutdown, process, memory, log-byte,
   and fixed-sample latency deltas; then execute the complete F02 exit gate.

## Design Boundaries

- W3C `traceparent` semantics and OpenTelemetry context/span conventions own
  interoperability. F02 must not create a bespoke identifier protocol.
- Each web/API boundary has one instrumentation owner. Automatic and manual
  instrumentation may not emit duplicate spans or events.
- Incoming trace data is untrusted. Invalid length, alphabet, version, flags,
  all-zero identifiers, excess state, or injection attempts create a safe new
  root or fail closed according to the standard; untrusted values are never
  copied into free-form diagnostics.
- Context is request-scoped and reset in `finally`-equivalent cleanup. Async and
  concurrent tests must prove no bleed between requests or after completion.
- Diagnostic events accept only enumerated event names, safe reason codes,
  numeric durations/counts, and validated trace/span identifiers. They do not
  accept raw URLs, query strings, headers, bodies, response content, exception
  text, environment values, user text, or arbitrary extra fields.
- The existing health schema and accessible UI states remain unchanged. Trace
  context is server-only and is not a public response or browser contract.
- F02 emits and verifies diagnostics only around the existing `/health/live`
  server-to-server transaction. It does not pre-instrument future product routes.
- No exporter is configured. In-process test capture or a cleaned temporary
  harness artifact may verify behavior, but F02 creates no persistent diagnostic
  store, network egress, telemetry backend, sampling policy, or retention policy.

## Dependency Decision Rule

Before adding a package in F02-01, record the evaluated standard-library and
OpenTelemetry-compatible options, exact responsibility, transitive and lockfile
delta, install/runtime cost, failure mode, upgrade surface, and replacement
path. Select the smallest maintained option that implements the approved W3C and
OpenTelemetry boundary without an exporter or vendor SDK. A package is not
approved merely because it is popular, and a custom protocol is not an allowed
way to avoid a dependency.

## F02-01 Dependency and Ownership Decision

F02-01 evaluated four options. A standard-library parser was rejected because
it would make this repository own a bespoke W3C protocol and compatibility
surface. `opentelemetry-api` alone was rejected because it cannot own an
application-local recording provider. Broad ASGI/FastAPI auto-instrumentation,
logging instrumentation, distributions, exporters, and vendor SDKs were
rejected because they expand route coverage, attributes, duplication, egress,
and upgrade surface. The selected boundary is the exact pair
`opentelemetry-api==1.43.0` and `opentelemetry-sdk==1.43.0`; both are direct
dependencies because production code imports both. The SDK resolves
`opentelemetry-semantic-conventions==0.64b0`, while its other dependency,
`typing-extensions`, was already locked.

The API owns W3C types and the official `TraceContextTextMapPropagator`. The SDK
owns one application-local `TracerProvider`, a parent-based always-on root
sampler, span creation, and provider shutdown. No global provider is set. No
span processor, exporter, backend, automatic instrumentation, worker, network
request, or retained store is configured. One pure-ASGI middleware owns only
`GET /health/live`, creates a safe root for absent or rejected context, and
emits exactly one fixed completion event through an injectable in-process sink.
The 512-byte inbound cap is an application resource policy, not a W3C maximum;
future versions and reserved flag bits remain delegated to the official parser.

The three added wheels total 444,477 bytes. The manifest grew from 1,061 to
1,123 bytes and the lockfile from 68,308 to 71,014 bytes. A warm locked sync was
61 ms after the change versus the prior 140 ms warm observation; these cache-
sensitive timings are observations, not an install budget. API and SDK versions
must move together under a locked dependency review; the transitive semantic-
conventions version must be re-inspected on upgrade. Rollback removes the two
pins, regenerated lock entries, middleware/runtime/event modules, and wiring.
The provider-neutral replacement boundary is the event sink plus app-local
runtime, so a later approved implementation can replace the SDK without changing
the health response or accepting a vendor contract.

Instrumentation setup, monotonic-clock, and event-sink failures fall back to the
unchanged health operation without logging their exception. Invalid or hostile
context creates a safe root. Configuration failure exits nonzero through a fixed
generic bootstrap event without reproducing validation input or a traceback.
The application lifespan shuts down the empty provider. The remaining upgrade
risk is OpenTelemetry's coupled API/SDK and semantic-conventions release train;
no public response, schema, migration, data, storage, external API, or model
compatibility surface changes in F02-01.

The post-change fixed sample (20 warmups, 500 in-process requests) observed
1.020 ms p50, 1.728 ms p95, and 2.312 ms maximum versus the pre-change 0.855 ms
p50, 1.386 ms p95, and 4.743 ms maximum. Each measured request produced one
265-byte compact diagnostic event. A Windows cross-process smoke observed API
liveness in 1,668 ms, total smoke in 4,681 ms, and shutdown in 255 ms. Exact
Ubuntu runtime-smoke job `87219208633` observed API liveness in 2,633 ms, four
owned processes, 716,132,352 aggregate resident bytes, 16,368,938 Next.js build
bytes, total smoke in 6,213 ms, and shutdown in 251 ms. External API, model,
telemetry-egress, and telemetry-storage cost remain zero.

## F02-02 Dependency and Ownership Decision

F02-02 evaluated four web-side approaches. Hand-generating identifiers and a
`traceparent` string was rejected because it would make this repository own a
bespoke interoperability surface. `@opentelemetry/api` alone was rejected
because its default tracer is non-recording and cannot own the real span and
identifiers required by the cross-process boundary. Next.js `instrumentation.ts`,
`@vercel/otel`, `@opentelemetry/sdk-node`, and HTTP/fetch auto-instrumentation
were rejected because they broaden ownership beyond one health call, may select
a deployment runtime, and can introduce duplicate spans or attributes. The
selected exact direct dependencies are `@opentelemetry/api@1.9.1`,
`@opentelemetry/core@2.9.0`, and
`@opentelemetry/sdk-trace@2.9.0`. Production imports the API types and root
context, core's official `W3CTraceContextPropagator`, and the trace SDK's
low-level private `TracerProvider`, so each package is a direct dependency
rather than an accidental transitive import. The lower-level provider was
selected after verification showed that the base SDK provider parses ambient
`OTEL_*` configuration during construction; F02-02 must not let deployment
environment values broaden or disable its fixed app-local behavior.

The selected trace SDK resolves `@opentelemetry/resources@2.9.0` and
`@opentelemetry/semantic-conventions@1.43.0`. All resolved Node constraints are
compatible with the repository's `>=20.9.0 <26` range. The provider is
application-local with an explicit parent-based always-on root sampler and an
empty processor list. It is never globally registered, has no context manager,
exporter, worker, socket, persistence, or egress, and starts each client span
against explicit `ROOT_CONTEXT`. The official propagator injects into a
temporary carrier; only a canonical validated `traceparent` whose identifiers
match the span is copied into the server-only fetch. Browser or ambient Next.js
context, baggage, `tracestate`, cookies, credentials, and arbitrary headers are
not read or forwarded.

Next.js 16.2.10 declares `@opentelemetry/api` as an optional peer, so the direct
pin activates one shared API singleton for Next.js and this private provider.
Current F02-02 code performs no global registration, making that shared package
inert outside this explicit call path. Any future global provider,
`instrumentation.ts`, or automatic-instrumentation change must review this
singleton boundary first because it could allow framework-owned tracing to
observe or duplicate the health transaction.

The web health adapter retains one attempt, the positive timeout validation,
the existing `AbortController`, the 2,000 ms runtime bound, `no-store`, omitted
credentials, rejected redirects, exact 200/media-type/JSON/contract checks, and
the unchanged public result union. A request-local idempotent completion emits
one frozen allowlisted `web.health.request.completed` JSON line to standard
error with only schema, service, operation, outcome, result, reason, validated
trace/span identifiers, numeric status, and elapsed milliseconds. Setup,
propagation, clock, span-status, span-end, sink, and completion failures suppress
diagnostics without changing the health result. Unexpected adapter failures
emit only `application_error`, end the span, and rethrow the original failure.
No URL, header, body, response detail, environment value, exception text, or
arbitrary field enters the event.

The manifest grew from 785 to 1,025 bytes and the lockfile from 252,035 to
254,732 bytes, deltas of 240 and 2,697 bytes. The five installed OpenTelemetry
package directories contain 14,822,615 bytes. A clean post-change `npm ci`
completed in 66,659 ms and `npm audit` reported zero vulnerabilities; install
repeated allow-script warnings for the already locked `sharp` and
`unrs-resolver` packages, neither of which F02-02 changes. A clean production
build completed in 9,619 ms and produced 4,335,774 `.next` bytes. No comparable
clean opening snapshot was retained, so that server-output value is an
observation rather than a claimed delta. All 10 browser assets remained exactly
629,565 bytes and the enforced confidentiality scan passed; a temporary banned
marker then made the scan fail nonzero before removal, and the clean scan passed
again.

The final Windows runtime smoke started from an absent `.next/dev` cache and
observed it grow from zero to 16,998,393 bytes, API liveness in 1,936 ms, total
smoke in 4,031 ms, and shutdown in 155 ms. Process and resident-memory readings
were unavailable on this Windows host, both fixed ports closed, and logs showed
one matching trace ID across the web and API events with distinct span IDs.
That match remains an observation until F02-03 adds the deterministic
cross-process assertion.

A fixed 20-warmup, 500-call in-process observation measured the unchanged
adapter path at 0.049 ms p50, 0.120 ms p95, and 2.463 ms maximum, and the
instrumented path at 0.095 ms p50, 0.210 ms p95, and 0.709 ms maximum. Exactly
500 events were captured at 260 UTF-8 bytes each. These are local observations,
not product or production budgets. External API, model, telemetry-egress, and
telemetry-storage cost remain zero. Upgrades must review the three direct pins
and resolved semantic-conventions release together. Rollback removes those
pins, the web diagnostic module, adapter wiring, focused tests, and browser
scan; the F01 health response and UI contract then remain intact.

## F02-01 Acceptance Evidence

Implementation revision `1cd879ef9a37dc04a28c09e7fed23d40441fdb3c`
completed exact GitHub Actions run `29372599433` successfully in 1 minute 28
seconds. API quality job `87219074832` passed locked synchronization, both
canonical contracts, Ruff, strict mypy, line endings, and all 186 tests in 3.00
seconds at 99% coverage. Web quality job `87219074897` passed lint, strict
typecheck, all 74 tests, and the production build. Runtime-smoke job
`87219208633` passed the unchanged cross-process contract, resource, cleanup,
and port-closure gates. This accepts F02-01 only; F02 remains `IN_PROGRESS` with
a null phase gate until F02-02, F02-03, and the complete exit gate pass.

## Failure Handling

- Malformed external context never crashes a request or poisons another request.
- Instrumentation failure may reduce diagnostics but must not change the health
  result, extend its two-second bound, expose internal values, or create a false
  success classification.
- Sensitive diagnostic input fails closed before formatting. Raw exception text
  is neither a fallback field nor a safe reason code.
- Duplicate instrumentation, unbounded cardinality, context bleed, a canary
  leak, browser exposure, or unexpected egress is a phase-gate failure.
- A failed cross-process design is narrowed or revised; it is not repaired by
  selecting a telemetry vendor or inventing product identifiers.

## Test Strategy

F02-01 requires focused API unit and integration tests for valid, absent,
malformed, hostile, and oversized context; zero identifiers; fixed fields;
canary redaction; exception paths; nested and concurrent requests; cleanup; and
duplicate emission. F02-02 requires focused web tests for standard injection,
safe outcome/timing events, timeout and fetch behavior, server-only boundaries,
and browser-output confidentiality. F02-03 requires a deterministic real-process
success/failure harness on Windows and the supported Ubuntu CI runner.

All affected F00/F01 locked dependency, format, lint, strict type, unit,
contract, coverage, build, lifecycle, and smoke gates remain mandatory. Tests
must prove behavior and confidentiality; coverage exclusions cannot substitute
for adversarial execution.

## Performance and Resource Observations

Record dependency and lockfile bytes, install delta, startup and shutdown time,
process count, aggregate resident memory, diagnostic records and UTF-8 bytes per
health transaction, and fixed-sample p50/p95 health latency before and after F02.
No new platform threshold is invented; an unexplained regression is reviewed and
may return `Revise`. External API/model cost, telemetry egress, and telemetry
storage cost must remain zero.

## Data, Privacy, and Compatibility

F02 adds no migration, database, retained telemetry, user record, learner data,
or production data flow. Trace and span identifiers are technical correlation
values, not identity or evidence. The existing health OpenAPI response, generated
TypeScript validator, web result union, and accessible page remain compatible.
This phase does not constitute a privacy review, audit record, production
observability claim, or `V17A` evidence.

## Non-Goals

- Database, ORM, migration, schema, repository, event, outbox, replay,
  projection, or background-job implementation.
- Authentication, authorization, role, learner, competency, curriculum,
  assessment, mastery, evidence, artifact, simulation, or readiness behavior.
- Product analytics, learner/session/attempt correlation, audit history,
  operational budgets, alerting, monitoring, dashboards, or SLOs.
- Browser telemetry, client tracing, exporter/backend/vendor selection, network
  egress, production sampling or retention, deployment, or LLM access.
- Any change to V00 evidence, V01 eligibility, V02 ownership, V17A evidence, or
  product claims.

## Acceptance Criteria

F02 passes only when every roadmap exit condition is met, all three slices are
independently verified, the exact pushed revision passes the full GitHub Actions
workflow, resource observations are recorded, and the inventory/controller are
internally consistent. Passing F02 does not pass V00, unlock V01, authorize V02,
or approve telemetry for production.

## Rollback Strategy

Each slice must remain independently revertible. Reverting F02 restores the F01
health transaction and logging behavior without changing its OpenAPI contract,
process ownership, or web availability states. No data rollback exists because
F02 creates no persistent data or migration.

## Gate Decision Rules

- `Continue`: every F02 exit condition passes on the exact pushed revision.
- `Revise`: correlation, confidentiality, isolation, duplication, compatibility,
  test, or resource evidence fails but can be repaired within the phase.
- `Narrow`: cross-process work would require browser telemetry, production
  topology, a backend/vendor choice, or another broader capability; amend the
  phase before proceeding.
- `Stop`: useful diagnostics require raw sensitive content, product/domain
  identifiers, persistent telemetry, a vendor commitment, or bypassing a
  validation gate.

## Exact Next Action

Commit and push the independently accepted `F02-02 - Server-to-server
propagation` revision, then require exact GitHub Actions acceptance. Do not start
F02-03, evaluate the F02 phase gate, or add deployment configuration in this
invocation.
