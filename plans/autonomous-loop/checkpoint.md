# Autonomous Loop Checkpoint

## Current phase and gate

Foundation phase `F02 - Cross-Process Correlation and Confidential Diagnostics
Baseline` is `PHASE_PASSED / Continue`. Validation remains `V00 - Candidate Role
Evidence`, `WAITING_EXTERNAL / Revise`; V01 remains locked. The controller stops
before another phase, and no human review is pending.

## Accepted implementation

F02-03 keeps the unchanged root smoke command and launches a private isolated
runtime proof. It validates exact bounded API/web/process schemas, 21 correlated
requests, W3C parent relationships, distinct spans, safe absent/malformed roots,
a four-request overlap barrier, available/unavailable/invalid fixture outcomes,
response and browser confidentiality, bounded stderr capture, resources,
cancellation, descendant cleanup, process reaping, and closed ports. Its public
aggregate contains only counts, byte totals, resources, lifecycle values, and
fixed-sample timings.

Independent verification identified seven concrete lifecycle, concurrency,
schema, header, and capture defects; each was repaired and regression tested.
The verifier's final rereview was unavailable after quota exhaustion, so the
controller performed the required read-only fallback audit and repaired one
additional launch-to-capture interruption race.

## Local evidence

- 108 focused runtime-smoke tests passed.
- 250 API tests passed in 11.75 seconds at 97% branch-aware coverage; `smoke.py`
  is 95% and the supervisor is 99%.
- Locked sync, both contract checks, Ruff, and native/Linux/Win32 mypy passed
  across 26 files.
- All 97 web tests, lint, typecheck, production build, and the 10-file,
  629,565-byte browser confidentiality scan passed.
- The final Windows smoke produced 48 events and 21 correlations, completed in
  4,269 ms, shut down in 51 ms, and closed both ports.

## Exact GitHub Actions acceptance

Implementation SHA `82736aff83c0c4fce66b31095b65fdc7e57d1c5f` was
rejected by run `29509035888` after API and web passed but runtime-smoke found an
Ubuntu-only forbidden raw marker. The value was suppressed. The `Revise` repair
added only a fixed safe failure category; it did not allow or emit raw content.

Revised SHA `16bf84c9919ccf16d1e06e1542245737bd61cde4` passed exact
run `29510082305`. Initial jobs were API `87660936291`, web `87660936295`, and
runtime-smoke `87661156124`. The controller then reran the full dependent job
chain twice; runtime jobs `87661534645` and `87661831197` also passed. Every
Ubuntu runtime attempt produced exactly 48 events, 21 correlations, four
concurrent workers, four owned processes, bounded output, and closed ports.
Observed ranges were 841,670,656-844,980,224 resident bytes, 1,832-2,340 ms API
liveness, 5,012-7,554 ms total smoke, and 50-403 ms shutdown.

## Risks and boundaries

The source of the first Ubuntu-only raw-marker failure remains unknown and is a
residual flake risk. Three consecutive clean attempts on the accepted revision
reduce but do not erase that uncertainty; any recurrence now fails with a safe
category and still suppresses the raw value. The tracked 66.3 MB archive remains
an unrelated checkout-cost risk. F02 adds no persistent telemetry, exporter,
backend, migration, product/learner identifier, or external cost.

V00 still lacks qualifying symmetric demand evidence, two qualified practitioner
confirmations, a confirmed channel owner able to reach 20-50 eligible adults,
and acceptable measured expected-cost evidence. Those inputs cannot be
self-certified. Vercel remains a provisional deployment candidate only;
deployment is a separate gated phase.

## Exact next action

Publish this controller acceptance commit and require its own API, web, and
runtime-smoke Actions jobs to pass. Then stop before the next phase.
