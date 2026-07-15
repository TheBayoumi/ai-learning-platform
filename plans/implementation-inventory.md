# Implementation Inventory

Generated from exact-CI-accepted F02-02 implementation revision
`b6550c58f4342a82197455f53eb064a32306e8fc`. The machine-readable record is
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
  F02-01 is accepted: exact OpenTelemetry API/SDK pins now own an
  app-local, exporter-free provider; one pure-ASGI boundary validates W3C context
  for `GET /health/live`, creates safe roots, restores concurrent context, emits
  one fixed confidential event, suppresses raw process/access/error logs, and
  fails closed at bootstrap. Focused adversarial tests, 99% full API coverage,
  strict native/Linux/Windows typing, both contracts, and the Windows smoke pass
  locally. Independent final rereview returned `ACCEPT` with no actionable
  finding. Exact revision `1cd879ef9a37dc04a28c09e7fed23d40441fdb3c`
  then passed Actions run `29372599433`: API quality passed 186 tests in 3.00
  seconds at 99% coverage; web quality passed 74 tests and the production build;
  runtime smoke observed four owned processes, 716,132,352 resident bytes, 2,633
  ms API liveness, 6,213 ms total smoke, 251 ms shutdown, and both ports closed.
  F02-02 is accepted: the Next.js server now owns one private client
  span, injects one canonical `traceparent`, emits one fixed completion event,
  preserves every F01 health classification and bound, and enforces a browser
  asset confidentiality scan. Its 61 focused tests, 97-test full web run,
  production build, hostile ambient-configuration and response-detail canaries,
  500-call resource observation, all affected API gates, and Windows smoke pass
  locally. Independent final verification returned `ACCEPT` with no actionable
  finding. Exact revision `b6550c58f4342a82197455f53eb064a32306e8fc`
  then passed Actions run `29400137315`: API quality passed 186 tests in 2.45
  seconds at 99% coverage; web quality passed all 97 tests, locked install,
  lint, strict typecheck, the production build, and browser confidentiality
  scan; runtime smoke observed matching web/API trace IDs with distinct spans,
  four processes, 747,077,632 resident bytes, 1,924 ms API liveness, 4,773 ms
  total smoke, 252 ms shutdown, and both ports closed. F02-03, exporters,
  backend, product metrics, learner
  identifiers, and V17A behavior remain absent.
- GitHub remains the source, CI, and exact-revision acceptance control plane.
  The user reports a Vercel Git connection; Vercel is the provisional deployment
  candidate because current official support includes FastAPI Python Functions
  and combined Next.js/FastAPI Services. No local link or deployment config is
  verified, those surfaces are beta/constrained, and they conflict with the
  currently approved container runtime unless a later gated phase reconciles or
  amends that decision. No deployment is implemented in F02.
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
| F02 | Foundation | `IN_PROGRESS` | F02-01 and F02-02 accepted; F02-03 remains |
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
deterministic bounded local/CI health-contract smoke. Accepted F02-01 adds one
app-local W3C context/span and fixed allowlisted event for API liveness, with no
exporter or global provider. Accepted F02-02 adds one private web client
span, server-only W3C propagation, one fixed safe web event, and a production
browser-asset confidentiality gate.
The repository has no persistent telemetry,
authentication, learner or role state, events/outbox/replay, competency graph,
curriculum, assessment, tutoring, LLM access, mastery, readiness, unique work,
simulation, provenance, privacy lifecycle, jobs, telemetry backend, or
deployment.

## Next Inventory Update

On a later invocation, revalidate entry and implement only F02-03 cross-process
proof and phase exit. Keep F02 `IN_PROGRESS` with a null phase gate until that
slice and the complete exit gate pass. Do not treat F01 or F02 as evidence for
V00.
