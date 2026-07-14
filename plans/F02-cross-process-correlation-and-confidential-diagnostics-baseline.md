# ExecPlan: F02 Cross-Process Correlation and Confidential Diagnostics Baseline

**Phase:** `F02 - Cross-Process Correlation and Confidential Diagnostics Baseline`
**Class:** Technical foundation
**Status:** In progress - F02-01 implemented locally; exact pushed CI pending
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

1. `F02-01 - API diagnostic context` (**implemented locally; exact CI pending**): record the minimal instrumentation
   dependency/ownership decision; define a fixed safe event vocabulary; add W3C
   context validation, safe-root creation, API middleware/context isolation, and
   allowlisted JSON diagnostics; replace or suppress unsafe raw request/error
   logging; and prove malformed-input, canary-redaction, concurrency, cleanup,
   and exact-count behavior.
2. `F02-02 - Server-to-server propagation`: create and propagate context only
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
liveness in 1,668 ms, total smoke in 4,681 ms, and shutdown in 255 ms; local
process/resident-memory collection was unavailable, so exact Ubuntu CI remains
the resource gate. External API, model, telemetry-egress, and telemetry-storage
cost remain zero.

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

Commit and push only the locally accepted `F02-01 - API diagnostic context`
revision, then require its exact API, web, and runtime GitHub Actions jobs. Do
not start F02-02 before F02-01 is accepted.
