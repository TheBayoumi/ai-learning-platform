# Implementation Inventory

Generated from the repository on 2026-07-12 at commit
`b69648193ab420d0f7e7a2fccb2a66296a8ec57b` plus the uncommitted, locally
verified F00 and F01-01 through F01-06 slices. The machine-readable record is
`plans/implementation-inventory.json`. Roadmap prose is not counted as runtime
implementation.

## Current Evidence

- F00 is implemented and independently verified: 5 API tests passed with 96%
  coverage, 1 web test passed, both locked installs succeeded, a real API served
  live/ready/OpenAPI, and the default production build completed.
- V00 has documentation and evidence-request artifacts, but its conjunctive gate
  is not passed. Approved demand, practitioner, and cost rules plus external
  practitioner/recruitment evidence remain absent.
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
  pass. F01 is `BLOCKED_EXTERNAL`, not passed, because the uncommitted revision
  has no successful supported-Ubuntu CI run or Linux resource observation.
- V01-V22 and the Q2-Q4 horizons have no runtime implementation. Each is locked
  by failed prerequisite evidence recorded in the JSON inventory.

## Phase Summary

| Phase | Lane | Status | Entry result / next action |
| --- | --- | --- | --- |
| F00 | Foundation | `PASSED` | Exit gate verified; no further F00 implementation |
| F01 | Foundation | `BLOCKED_EXTERNAL` | Local exit gate passes; exact-revision Ubuntu CI evidence remains |
| V00 | Validation | `BLOCKED_HUMAN` | Entry passed; human rules and external evidence block its exit gate |
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
The repository has no persistence, authentication, learner or role
state, events/outbox/replay, competency graph, curriculum, assessment, tutoring,
LLM access, mastery, readiness, unique work, simulation, provenance, privacy
lifecycle, jobs, telemetry backend, or deployment.

## Next Inventory Update

Recompute only entries affected by new roadmap definitions, controlled V00
evidence, executable changes, or exact-revision CI evidence. F01-06 adds no
readiness, client state, or domain behavior. The sole next action is to obtain
explicit authorization to commit and push the intended F00/F01 files, then
require a successful current-revision Ubuntu CI run before passing F01.
