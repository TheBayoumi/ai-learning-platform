# Implementation Inventory

Generated from exact-CI-verified executable revision
`2bc6dfa392725ea725dda6915a7d6ab68a246251`, exact-CI-verified F02-definition
revision `6de13bba593e4b7aae30f112feb4a22a106ef7e2`, and this independently reviewed
controller-authority amendment. The machine-readable record is
`plans/implementation-inventory.json`. Roadmap prose and controller state are
not counted as runtime implementation.

## Current Evidence

- F00 is implemented and independently verified: 5 API tests passed with 96%
  coverage, 1 web test passed, both locked installs succeeded, a real API served
  live/ready/OpenAPI, and the default production build completed.
- V00 has documentation and evidence-request artifacts, but its conjunctive gate
  is not passed. Codex now owns preregistration and application of the demand,
  practitioner, and cost rules without separate user approval. Qualifying
  demand, practitioner, recruitment, and measured cost evidence remain absent.
- F01 has passed entry conditions. F01-01 now generates and byte-checks a
  canonical health-only OpenAPI artifact, with 10 focused tests and CI/local
  command parity. F01-02 now derives a dependency-free TypeScript type and
  runtime guard from that artifact. Independent review accepted its derivation,
  semantics, tests, portability, and scope. F01-03 now adds a canonical
  server-only loopback origin and replaceable bounded liveness adapter; its 52
  focused and 56 full web tests and affected gates pass. Independent review
  accepted its boundaries, behavior, tests, confidentiality, dependencies, and
  scope. F01-04 now adds a request-time, server-rendered accessible local API
  status surface; its 19 focused and 74 full web tests and all affected local
  gates pass. Independent review accepted its runtime wiring, accessibility,
  confidentiality, visual hierarchy, dependencies, and scope. F01-05 now adds
  the fixed development supervisor: 37 focused tests pass at 96% supervisor
  coverage, and actual Windows startup, clean shutdown, forced-tree,
  leader-exit descendant cleanup, and induced-failure behavior pass. Independent
  review accepted ownership safety, portability boundaries, tests, resources,
  CI scope, and lane protection. F01-06 now adds the identical local/CI
  cross-process smoke: 44 focused and 126 full API tests pass at 98% smoke and
  97% total coverage; all 74 web tests, the API-absent dynamic build, the exact
  Windows live smoke, cleanup, confidentiality scan, and complete local gates
  pass. Pushed revision `34fe4465e567a562f22b7c63bd6d5df29fdef09a`
  repaired Linux mypy. Exact Actions run `29359471181` passed API sync, both
  contract checks, Ruff, strict mypy, and all 127 tests in 2.05 seconds, then
  failed coverage at 92% total and 84% supervisor because Ubuntu did not execute
  the Windows Job Object and suspended-thread helper branches. Web quality
  passed 6 files and 74 tests; runtime smoke was skipped by the failed API
  dependency. Behavior-driven fake-kernel coverage passes 47 focused and 136
  full API tests locally at 99% coverage without exclusions. Exact revision
  `2bc6dfa392725ea725dda6915a7d6ab68a246251` then passed Actions run
  `29363263721`: API quality passed 136 Linux tests at 99% coverage; web quality
  passed 74 tests and the production build; runtime smoke passed with 4 owned
  processes, 714,330,112 resident bytes, 2,541 ms API liveness, 6,359 ms total
  smoke, 251 ms shutdown, and both ports closed. Independent review accepted the
  repair and boundaries. F01 is `PASSED / Continue`; it adds no validation-lane
  evidence and does not unlock V01.
- F02 is now formally defined as a cross-process correlation and confidential
  diagnostics baseline around the existing server-rendered health transaction.
  Architecture review preferred it over PostgreSQL because it adds no external
  service or persistent metadata and selects no provisional migration tooling.
  F02 is `NOT_STARTED`: no source, dependency, workflow, test, runtime, exporter,
  backend, product metric, learner identifier, or V17A behavior was added. Exact
  revision `6de13bba593e4b7aae30f112feb4a22a106ef7e2` passed GitHub Actions run
  `29367566575` across API, web, and runtime-smoke jobs.
- GitHub is recorded as the source, CI, environment-governance, and deployment
  control plane. GitHub Pages is not treated as a runtime deployment because it
  cannot host this FastAPI plus server-rendered Next.js architecture. A real
  containerized managed-PaaS deployment remains absent and separately gated.
- The externally created commit also tracks the unrelated 66,312,302-byte
  `ai-learning-platform.7z`. This repair does not modify it; its repository and
  CI-checkout cost remains an explicit scope risk.
- Four protected V00 Markdown working copies remain mixed-EOL locally while
  their index blobs are LF and Git reports no content diff. This API repair does
  not rewrite validation evidence; a clean Linux checkout retains the indexed
  LF form.
- V01-V22 and the Q2-Q4 horizons have no runtime implementation. Each is locked
  by failed prerequisite evidence recorded in the JSON inventory.

## Phase Summary

| Phase | Lane | Status | Entry result / next action |
| --- | --- | --- | --- |
| F00 | Foundation | `PASSED` | Exit gate verified; no further F00 implementation |
| F01 | Foundation | `PASSED` | Exact Ubuntu API, web, lifecycle, smoke, and resource gates passed |
| F02 | Foundation | `NOT_STARTED` | Entry conditions pass; implement only F02-01 on a later invocation |
| V00 | Validation | `BLOCKED_EXTERNAL` | Entry passed; Codex owns rule decisions, while real external evidence blocks exit |
| V01 | Validation | `NOT_STARTED` | V00 candidate, practitioners, and recruitment channel absent |
| V02 | Validation | `NOT_STARTED` | V01 has not passed |
| V03 | Validation | `NOT_STARTED` | V02 contracts do not exist |
| V04 | Validation | `NOT_STARTED` | V01 and V02 have not passed |
| V05 | Validation | `NOT_STARTED` | V04 has not passed |
| V06 | Validation | `NOT_STARTED` | V05 and reviewer availability are absent |
| V07 | Validation | `NOT_STARTED` | V03 and V06 have not passed |
| V08 | Validation | `NOT_STARTED` | V03, V05, and V07 have not passed |
| V08R | Validation | `NOT_STARTED` | V08 and applicable validators are absent |
| V09 | Validation | `NOT_STARTED` | V03 and V07 have not passed |
| V10 | Validation | `NOT_STARTED` | V05, V07, and V09 have not passed |
| V11 | Validation | `NOT_STARTED` | V04, V09, and V10 have not passed |
| V12 | Validation | `NOT_STARTED` | V05, V09, and V11 have not passed |
| V13 | Validation | `NOT_STARTED` | V12 and a viable 30-day observation plan are absent |
| V14 | Validation | `NOT_STARTED` | V05, V11, V13, and runner approval are absent |
| V15 | Validation | `NOT_STARTED` | V03 and V14 have not passed |
| V16 | Validation | `NOT_STARTED` | V09 and V12-V15 have not passed |
| V16A | Validation | `NOT_STARTED` | V02/V03 and a stable deployment shape are absent |
| V16B | Validation | `NOT_STARTED` | V03/V16A and reviewable vendors/data flows are absent |
| V17A | Validation | `NOT_STARTED` | V08/V09/V11 and representative jobs are absent |
| V17B | Validation | `NOT_STARTED` | V07-V17A and real beta access have not passed |
| V17C | Validation | `NOT_STARTED` | V17B and calibration controls are absent |
| V18 | Validation | `NOT_STARTED` | V17C and an eligible beta timeline are absent |
| V19 | Validation | `NOT_STARTED` | No eligible longitudinal observations exist |
| V20 | Validation | `NOT_STARTED` | V14-V16 and eligible proof-slice evidence are absent |
| V21 | Validation | `NOT_STARTED` | V17A cost data and instrumented V18 are absent |
| V22 | Validation | `NOT_STARTED` | V19-V21 and all prior gates are incomplete |
| Q2 | Validation | `NOT_STARTED` | Requires a V22 Continue decision |
| Q3 | Validation | `NOT_STARTED` | Requires credible complete-role evidence and repeatable authoring |
| Q4 | Validation | `NOT_STARTED` | Requires proof that the first role is repeatable, not bespoke |

## Runtime Capability Boundary

Implemented runtime behavior is limited to process configuration/logging, two
configuration-only health endpoints, canonical byte-checked OpenAPI generation,
an OpenAPI-derived TypeScript health type guard, canonical server-only loopback
configuration, a replaceable bounded liveness adapter, a request-time
server-rendered technical status surface with three accessible API states, a
development-only fixed API/web supervisor with bounded owned-tree cleanup, and a
deterministic bounded local/CI health-contract smoke.
The repository has no cross-process correlation or allowlisted confidential
diagnostic event boundary, persistence, authentication, learner or role
state, events/outbox/replay, competency graph, curriculum, assessment, tutoring,
LLM access, mastery, readiness, unique work, simulation, provenance, privacy
lifecycle, jobs, telemetry backend, or deployment.

## Next Inventory Update

Recompute only entries affected by controlled V00 evidence, executable changes,
or exact-revision CI evidence. F01 is passed and adds no readiness, client state,
or domain behavior. On a later invocation, revalidate F02 entry conditions and
implement only F02-01. Do not treat F01 or F02 as evidence for V00, and do not
start F02-02 in the same invocation.
