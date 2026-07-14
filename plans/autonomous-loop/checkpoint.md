# Autonomous Loop Checkpoint

## Current phase and slice

Validation: `V00 - Candidate Role Evidence`, `WAITING_HUMAN / Revise`.
Foundation: `F01 - Local Runtime Integration and API Contract Baseline`,
`BLOCKED_EXTERNAL`; F01-06 is locally complete. `V01` remains locked.

## Verified gate state

F00 and F01-01 through F01-05 remain accepted. F01-06's identical local/CI
cross-process smoke is implemented and passes every local gate. F01 is not
phase-passed because the roadmap requires successful lifecycle, smoke, and
resource evidence from the exact intended revision on the supported Ubuntu CI
runner. The work is uncommitted and commit/push is not authorized.

Validation remains `Revise / WAITING_HUMAN`; every conjunctive V00 exit condition
remains unmet or unverified. F01 adds no role, learner, mastery, evidence, or
readiness state and does not unlock V01.

## Last completed action

Implemented F01-06's dependency-free root smoke command and dedicated Ubuntu CI
job. The smoke reuses F01-05 ownership and signal primitives, bounds startup and
requests, size-limits responses, verifies exact live/ready/OpenAPI/accessible-web
contracts, records resources, and requires owned-tree cleanup plus closed ports.

## Exact next action

Obtain explicit authorization to commit and push the intended F00/F01 files,
then require a successful current-revision Ubuntu CI run.

## Changed files

This run adds `scripts/smoke.py`, the API development smoke policy, and 44
focused tests. It exposes only the existing supervisor launch/signal primitives
for reuse and updates CI, README, the F01 ExecPlan, inventory, controller goal,
state, run log, and this checkpoint. Earlier work and the unrelated
`ai-learning-platform.7z` remain untouched.

## Validation results

Forty-four focused tests pass at 98% smoke-policy coverage. The final full API
suite passes 126 tests at 97% total coverage; locked sync, Ruff format/lint,
strict mypy, and both canonical checks pass. The unchanged web tree's current
evidence remains `npm ci`, lint, strict typecheck, 74 tests, and an API-absent
dynamic production build. Browser static assets contain no API environment
name, origin, or health path.

The exact Windows root smoke reached API liveness in 1,426 ms, completed all
assertions in 3,614 ms, shut down in 204 ms, and left no listener on ports 3000
or 8000. Focused failure tests cover late responses, cache/resource observation,
signals, transport and contract failures, cleanup, and safe diagnostics.
Independent verification reproduced format, lint, strict typing, 44 focused and
81 combined smoke/supervisor tests, 98% smoke coverage, empty index, and diff
hygiene and accepted the local slice after two confirmed repairs. `git diff
--check` passes, the index is empty, and the automation lock is removed at
finalization.

## Unresolved findings

No successful Ubuntu CI run exists for the uncommitted exact revision, so Linux
process-count/resident-memory and actual workflow conclusions are missing. Local
Node 25.2.1 differs from pinned Node 24.18.0 while remaining inside the declared
`<26` range. Four protected V00 Markdown working copies remain mixed-EOL locally
while their index blobs are LF; they were not modified.

## External blockers

F01 requires an exact-revision supported-Ubuntu CI run. V00 separately still
requires two qualified practitioners, a real 20-50-adult recruitment channel,
and privacy-safe confirmations.

## Human decisions required

Commit/push authorization is required before exact-revision CI can run. The V00
demand-sufficiency, practitioner-qualification, and expected-cost rules also
remain unapproved.

## Rollback point

`b696481` on `automation/v00-phase-loop`; no commit or push was performed.

## Another run may proceed automatically

No. Await commit/push authorization and remote CI evidence. Do not begin another
phase or V01.
