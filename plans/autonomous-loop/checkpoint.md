# Autonomous Loop Checkpoint

## Current phase and slice

Validation remains `V00 - Candidate Role Evidence`, `WAITING_EXTERNAL / Revise`.
Foundation is `F02 - Cross-Process Correlation and Confidential Diagnostics
Baseline`, `IN_PROGRESS`, with a null phase gate. Only `F02-01 - API diagnostic
context` is implemented locally and is `IMPLEMENTED_UNVERIFIED`; V01 is locked.

## Verified gate state

Starting revision `a35e1908f2d37dfcc2932d69bfd24a7bbd55dffd` passed exact
GitHub Actions run `29370109469` across API, web, and runtime-smoke jobs. F00 and
F01 remain passed. F02 entry conditions remain met, but F02 cannot pass until all
three slices and its exact exit gate pass.

F02-01 now owns an app-local OpenTelemetry provider and official W3C propagator,
strict inbound resource handling, safe-root creation, one span and one fixed
completion event only for `GET /health/live`, unconditional context cleanup,
confidential generic process logging, disabled Uvicorn access logging, and a
fail-closed bootstrap boundary. It configures no exporter, processor, backend,
global provider, telemetry persistence, or network egress.

Validation remains unchanged. No role, learner, mastery, evidence, readiness,
product analytics, audit, privacy approval, or V17A state was added. F02-01 is
not V00 evidence and does not unlock V01 or authorize V02.

## Last completed action

Implemented and locally verified only F02-01. Architecture and roadmap reviews
selected exact `opentelemetry-api==1.43.0` and
`opentelemetry-sdk==1.43.0`, with locked
`opentelemetry-semantic-conventions==0.64b0`, instead of a bespoke parser,
API-only no-op spans, broad auto-instrumentation, exporters, or vendor SDKs.

Independent verification found two material defects in the first draft. The
private v00 flag restriction was removed so reserved bits and future versions
are delegated to the official propagator. A real invalid-environment subprocess
proved that Uvicorn import failure bypassed the formatter and exposed raw
Pydantic input; `main.py` now emits one fixed generic event and exits nonzero
without a traceback. Both regressions now pass. The required dependency,
ownership, cost, failure, upgrade, rollback, and replacement decision is recorded
in the F02 ExecPlan.

## Exact next action

Complete the final read-only review and structural checks, commit and push only
this F02-01 slice, then require the exact revision's API, web, and runtime GitHub
Actions jobs. Do not start F02-02 before F02-01 is accepted.

## Changed files

The F02 ExecPlan and controller/inventory records; exact API dependency and lock
files; new diagnostic runtime, event, and pure-ASGI middleware modules; API app,
entrypoint, logging, and supervisor wiring; focused diagnostics and adjacent app
and supervisor tests; and the direct Uvicorn README command. No web source,
workflow, generated health contract, schema, migration, V00 evidence, or product
artifact changed. The tracked `ai-learning-platform.7z` remains untouched.

## Validation results

- Locked sync and `uv lock --check` pass. Both canonical health contract checks
  report current artifacts.
- Ruff format and lint pass. Native, Linux-targeted, and Windows-targeted strict
  mypy each pass all 26 source/test/script files.
- `apps/api/tests/test_api_diagnostics.py`: 50 focused adversarial tests pass.
  They cover valid, absent, malformed, hostile, duplicate, oversized, reserved-
  flag, and future-version context; safe roots; exact counts; canary suppression;
  concurrent/nested cleanup; response and route isolation; downstream,
  cancellation, clock, sink, propagator, and span-start failures; provider
  ownership; lifecycle; logging; and real invalid-configuration startup.
- The full API suite passes 186 tests in 15.32 seconds at 99% total line and
  branch coverage. The new diagnostic runtime, formatter, and middleware are at
  100% coverage without exclusions.
- A Windows cross-process smoke passes with unchanged health/OpenAPI/web
  contracts: API liveness 1,668 ms, total 4,681 ms, and shutdown 255 ms. Local
  process count and resident memory were unavailable; exact Ubuntu CI remains
  the resource gate.
- A fixed 500-request in-process sample observed 1.020 ms p50, 1.728 ms p95,
  and 2.312 ms maximum versus the pre-change 0.855/1.386/4.743 ms observations.
  Exactly 500 events were captured at 265 compact JSON bytes each.
- The manifest grew 62 bytes and lockfile 2,706 bytes; the three added wheels
  total 444,477 bytes. A warm locked sync was 61 ms. No process, worker, egress,
  persistence, external API, model, or telemetry-storage cost was added.
- Independent final rereview reproduced locked dependencies, formatting, lint,
  native/Linux/Windows typing, both contracts, all 186 tests and 99% coverage,
  Windows smoke, live and startup canary behavior, JSON, hashes, timestamps,
  scope, LF, secrets, and diff checks, then returned `ACCEPT` with no finding.

## Deployment maturity intent

GitHub remains source, CI, and exact-revision acceptance. The user reports a
Vercel Git connection, and current official documentation supports FastAPI
Python Functions plus combined Next.js/FastAPI Services. Vercel is therefore the
provisional deployment candidate, but there is no local link or `vercel.json`,
the relevant Vercel surfaces have beta/runtime constraints, and the function
topology conflicts with the approved container-managed-PaaS decision unless a
later gated phase reconciles or explicitly amends it. No deployment is part of
F02.

## Unresolved findings

F02-01 still needs exact pushed API/web/runtime CI acceptance. F02-02 web
propagation and F02-03 cross-process/resource exit evidence are absent. The
tracked 66.3 MB archive remains a repository/checkout-cost risk outside this
slice. V00 still lacks every required external evidence group.

## External blockers

F02 has none beyond its pending exact CI publication result. V00 still requires
qualifying demand evidence, two qualified practitioner confirmations, a real
20-50-adult recruitment channel, and acceptable measured expected-cost evidence.

## Human decisions required

None for F02-01 publication or acceptance. Constitutionally required human
evidence remains external and cannot be self-certified by Codex.

## Rollback point

`a35e1908f2d37dfcc2932d69bfd24a7bbd55dffd` on
`automation/v00-phase-loop`. F02-01 has no stored telemetry, migration, or data
rollback; removing its pins, modules, wiring, tests, and launch override restores
the F01 runtime.

## Another run may proceed automatically

No implementation run should start while this exact F02-01 publication gate is
pending. If it passes, a controller-only acceptance update may record F02-01 and
make F02-02 eligible for a later invocation. If it fails, repair only F02-01 and
return `Revise`.
