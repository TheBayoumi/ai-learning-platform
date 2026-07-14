# Autonomous Loop Checkpoint

## Current phase and slice

Validation: `V00 - Candidate Role Evidence`, `WAITING_HUMAN / Revise`.
Foundation: `F01 - Local Runtime Integration and API Contract Baseline`,
`FAILED_RETRYABLE / Revise`; the Linux coverage-portability repair is locally
verified and authorized for Codex publication. `V01` remains locked.

## Verified gate state

F00 and F01-01 through F01-06 remain locally accepted. Externally pushed
revision `34fe4465e567a562f22b7c63bd6d5df29fdef09a` reached Ubuntu CI in run
`29359471181`. API synchronization, both contract checks, Ruff, strict mypy,
and all 127 tests passed, but total coverage was 92% against the 95% gate because
the Windows Job Object and suspended-thread helpers were unexercised on Linux.
Web quality passed all 74 tests; runtime smoke was skipped after API failure.
Cross-platform fake-kernel tests now raise the local full suite to 136 passing
at 99% coverage without exclusions, but F01 is not phase-passed until the exact
repaired revision supplies successful API, web, lifecycle, smoke, and resource
evidence on the supported Ubuntu runner.

Validation remains `Revise / WAITING_HUMAN`; every conjunctive V00 exit condition
remains unmet or unverified. F01 adds no role, learner, mastery, evidence, or
readiness state and does not unlock V01.

## Last completed action

Added behavior-driven cross-platform tests for successful and failing Windows
Job Object creation and suspended-process resumption, including structure
configuration, thread selection, error provenance, and acquired-handle cleanup.

## Exact next action

Codex commits and pushes the verified coverage-portability repair, then monitors
the resulting exact-revision GitHub Actions run as the F01 gated review.

## Changed files

This run changes only supervisor tests and the F01 ExecPlan, inventory,
controller goal, state, run log, and this checkpoint. No production source,
dependency, lockfile, public schema, product behavior, or V00/V01 artifact
changes. The pre-existing, unrelated 66,312,302-byte
`ai-learning-platform.7z` remains tracked but untouched.

## Validation results

Exact run `29359471181` records 127 passing API tests in 2.05 seconds before the
coverage failure: `supervisor.py` was 84% and the API total was 92%. The web job
passed 6 files and 74 tests. Locally, 47 focused supervisor tests pass in 17.79
seconds and the full API suite passes 136 tests in 18.96 seconds; supervisor and
total coverage are 99%. Locked sync, both canonical checks, Ruff format and
lint, lock validation, and native, Linux-targeted, and Windows-targeted strict
mypy each pass all 23 files. Independent read-only coverage review accepted the
behavior-driven fake-kernel matrix without exclusions while retaining real
Windows lifecycle coverage.

## Unresolved findings

No successful Ubuntu CI run exists for the current coverage repair, so Linux
process-count/resident-memory and final workflow conclusions are missing. The
tracked 66.3 MB archive adds repository and CI-checkout cost and remains outside
the authorized repair scope. Four protected V00 Markdown working copies remain
mixed-EOL locally while their index blobs are LF and they have no content diff;
they were preserved rather than rewritten during this API repair.

## External blockers

F01 requires an exact-revision supported-Ubuntu CI rerun. V00 separately still
requires two qualified practitioners, a real 20-50-adult recruitment channel,
and privacy-safe confirmations.

## Human decisions required

No F01 commit/push decision remains: the user authorized Codex to publish bounded
verified repairs and use GitHub Actions as the gate. The V00 demand-sufficiency,
practitioner-qualification, and expected-cost rules remain unapproved.

## Rollback point

`34fe446` on `automation/v00-phase-loop` before this repair is committed.

## Another run may proceed automatically

Yes, but only to publish this verified bounded repair, monitor its exact Actions
run, and record the gate result. Do not begin another phase or V01 in this run.
