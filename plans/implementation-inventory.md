# Implementation Inventory

Current bounded repair records exact implementation head
`4e6770a1e1dcf2938f224c93c0701bae0e8e5f4c`, which passed Vercel deployment
status, the dedicated protected-page workflow, and all five exact GitHub quality
jobs. The dedicated non-production alias proof resolves
`f04.rollback_reversion`; the committed exact-SHA protected-page proof now also
resolves only `f04.deployed_page_verification`. F04 remains
`FAILED_RETRYABLE / Revise` with three blockers. F03 remains durably accepted;
F03/F04 are technical foundation, not product or validation evidence.
The machine-readable record is `plans/implementation-inventory.json`; this
prose is a synchronized human-readable projection.

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
  total smoke, 252 ms shutdown, and both ports closed.
  F02-03 is accepted: the unchanged root smoke command now owns an isolated,
  bounded real-process correlation, confidentiality, failure, resource, and
  lifecycle proof. It passes 108 focused tests, 250 full API tests at 97%
  coverage, all 97 web tests, static and contract gates, the production build,
  and the Windows root smoke. Exact classifier revision
  `16bf84c9919ccf16d1e06e1542245737bd61cde4` passed Actions run
  `29510082305`; its initial API, web, and runtime jobs plus two controller-run
  full-chain retries all passed. The three Ubuntu runtime attempts each produced
  exactly 48 events, 21 correlations, four concurrent workers, four owned
  processes, bounded output, and closed ports. F02 controller revision
  `8963101805d6f29f4701c91764b5563f07ff07c8` then passed exact run
  `29511515229`: API, web, and runtime-smoke jobs all succeeded. F02 is
  `PASSED / Continue`. Exporters, backend, product metrics, learner identifiers,
  V17A behavior, containers, and deployment remain absent.
- F03 is `PASSED` as the GitHub Phase-Gate Control Plane. Implementation
  attempt `9746ceb16a3bbfc1e95a8bfadae6224fe77dfe21` was correctly rejected by
  run `29521143904` because raw Windows CRLF checkout hashes did not match
  Linux LF bytes; canonical-LF hashing and a regression repaired it. Revision
  `34d5de2b5af15ec39e09b0f91ed5d358020dcfed` was rejected by exact run
  `29523254781` when Linux Runtime smoke captured a framework-owned raw URL;
  the corrected repair preserves F02's byte-for-byte outer validation and maps
  only ordinary framework stderr before capture. Implementation revision
  `fe49b609767e27d52fae999c229502ed98866dff` then passed exact GitHub Actions
  push run `29528587173` and pull-request run `29528587169`: API quality, Web
  quality, Runtime smoke, Phase gate, and Gate projection all succeeded on the
  exact SHA in both runs. Acceptance revision
  `c2938f2d0496088ea117acf387424530ad0b4c59` subsequently passed exact runs
  `29577006084` and `29577007722`, making F03 durably `PASSED / Continue`.
- GitHub remains the source, CI, exact-revision acceptance, and integration
  control plane.
- F04 - Vercel Deployment Baseline is `FAILED_RETRYABLE / Revise`. The topology decision
  required by GitHub issue #3 is recorded: `specs/tech-stack.md` approves
  "Containers on a managed PaaS" as the backend runtime (binding; only the
  vendor is Provisional), so F04 selects Option 2 — Vercel hosts only the
  Next.js web tier; the FastAPI API's deployment remains governed by the
  existing approved decision, with vendor selection deferred. Direct
  verification (`gh secret list`, GitHub check-runs, and commit-status
  queries) confirmed no Vercel secret or connected project existed before
  this phase began. A real Vercel account, organization, and project
  (`web`, scoped to `apps/web`) now exist via the Vercel CLI, with
  `.vercel/` and `.env.local` confirmed git-ignored and untracked. The user
  authorized a GitHub Login Connection on the Vercel account and ran
  `vercel git connect`, which succeeded; verified via the Vercel REST API
  that `link.type=github`, `link.repo=ai-learning-platform`. A real defect
  was found and fixed: the project's Root Directory was `.` (repo root,
  which fails Next.js detection); corrected to `apps/web` via
  `PATCH /v9/projects/{id}`, confirmed via a follow-up `GET`. Vercel's native
  GitHub App integration needs no repository secret for deployment. The later
  protected-page verifier uses short-lived `VERCEL_API_TOKEN` and
  `VERCEL_AUTOMATION_BYPASS_SECRET` Actions secrets under the documented
  trusted-push boundary; no value is committed or logged.
  `vercel rollback` returned HTTP 422 for the preview target; this remains
  rejected-command evidence, not traffic reversion.
  `f04-reversion-proof-web.vercel.app` subsequently moved B to prior preview A
  and back to intended final B through Vercel's supported alias API. Each
  transition verified exclusive alias ownership, exact deployment ID and SHA,
  `READY` preview state, and protected application HTTP without a redirect or
  confidential browser content. The Git-managed branch alias and production
  aliases were unchanged. Sanitized evidence is committed at
  `plans/F04-vercel-alias-reversion-evidence.json`.
  Exact deployed-page implementation revision
  `4e6770a1e1dcf2938f224c93c0701bae0e8e5f4c` passed dedicated workflow run
  `29865352967` and exact push Quality Gates run `29865352971`. Sanitized
  artifact `8508962218` binds GitHub deployment `5545146544` to `READY` preview
  `dpl_6U2FrqVs6paxCpnN7EaCd6dLMDTA`, the exact SHA/project/branch, protected
  HTTP 200 with no redirect, accessible API-unavailable semantics, and seven
  shared-rule-confidential browser assets. The focused suite passed 40 tests;
  independent rereview returned `PASS / Continue` after the PowerShell runbook
  was corrected to use the verified `npm.cmd` entrypoint. First record revision
  `cde7940a308ba81324713d1763a56908922b8886` then exposed a GitHub
  deployment-status propagation race in failed run `29866121231`: the exact
  deployment was visible before its status list. Empty lists now poll under the
  existing bound while malformed, ambiguous, and terminal statuses fail closed;
  all 41 focused tests, all 138 web tests, lint, strict typecheck, production
  build, confidentiality scan, and focused rereview pass. Exact resource revision
  `3f83e3e74d1fc587d90c30b1756c7f2dec994ba3` and run `29977879812` now
  commit the real build, footprint, cache, latency, runtime, and bounded cost
  evidence. No FastAPI deployment, PaaS vendor selection, or V00/V01
  evidence is introduced.
- Payload diagnostics confirmed the unrelated `ai-learning-platform.7z` was
  66,312,302 bytes and 97.6% of tracked blob bytes. This repair removes it from the
  current tree without history rewriting, updates its three references, and adds
  only `/ai-learning-platform.7z` to the root ignore file.
- Four protected V00 Markdown working copies remain mixed-EOL locally while
  their index blobs are LF and Git reports no content diff. This amendment does
  not rewrite validation evidence; a clean Linux checkout retains the indexed
  LF form.
- V01-V22 and the Q2-Q4 horizons have no runtime implementation. Each is locked
  by failed prerequisite evidence recorded in the JSON inventory.

## Phase Summary

| Phase | Lane | Status | Entry result / next action |
| --- | --- | --- | --- |
| F00 | Foundation | `PASSED` | Exit gate verified; no further F00 implementation |
| F01 | Foundation | `PASSED` | Exact Ubuntu API, web, lifecycle, smoke, and resource gates passed |
| F02 | Foundation | `PASSED` | Exact Ubuntu API, web, correlation, confidentiality, resource, and lifecycle gates passed |
| F03 | Foundation | `PASSED` | Implementation and acceptance revisions passed their own exact required runs |
| F04 | Foundation | `FAILED_RETRYABLE` | Verify payload hygiene, then publish the separate acceptance revision |
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
Accepted F02-03 adds the automated real-process correlation, safe-root,
concurrency, failure, confidentiality, event-volume, resource, and lifecycle
assertion.
F03 adds repository automation only: a standard-library policy validator,
  deterministic projection, and exact-head CI jobs. F04 has a verified remote
  Vercel preview for the existing Next.js web tier plus a committed exact-SHA,
  deployment-protection-aware page verifier, but no accepted reproducible
  deployment baseline, no deployed FastAPI API, and no production traffic alias.
  The current gates pass all 426 API tests at 97% coverage, all 138 web tests
  plus lint/typecheck/build/confidentiality, the 41-test focused verifier suite,
  and the final 48-event cross-process smoke. The supported B-to-A-to-B alias
  proof removes `f04.rollback_reversion`; the exact GitHub/Vercel deployment,
  protected HTTP, accessibility, and shared confidentiality chain removes
  `f04.deployed_page_verification`. Three F04 blockers remain.
The repository still has no OCI artifact or container harness. It also has no persistent telemetry, authentication,
learner or role state, events/outbox/replay, competency graph, curriculum,
assessment, tutoring, LLM access, mastery, readiness, unique work, simulation,
provenance, privacy lifecycle, jobs, or telemetry backend.

## Next Inventory Update

This bounded repair records the committed exact-SHA deployed-page proof while
keeping F04 `FAILED_RETRYABLE / Revise`. Require the bounded propagation-race
repair revision's own exact GitHub and Vercel checks to pass, record the
immutable proof durably in pull request #5 and issue #3, and stop. Do not treat
F00-F04 as V00 evidence. The only next eligible action is
`f04.build_reproducibility`.
