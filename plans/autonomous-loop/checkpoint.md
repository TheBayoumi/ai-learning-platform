# Autonomous Loop Checkpoint

## Current phase and slice

Validation: `V00 - Candidate Role Evidence`, `WAITING_HUMAN / Revise`.
Foundation: `F01 - Local Runtime Integration and API Contract Baseline`,
`FAILED_RETRYABLE / Revise`; the Linux mypy portability repair is locally
verified. `V01` remains locked.

## Verified gate state

F00 and F01-01 through F01-06 remain locally accepted. Externally pushed
revision `25994d214ed5b39d4b6c73ba0e075b10ee4a5a66` reached Ubuntu CI, where API
quality failed at strict mypy with 10 references to Windows-only `ctypes` APIs.
The two-file repair is locally verified without ignores, but F01 is not
phase-passed because the repaired exact revision still requires successful API,
web, lifecycle, smoke, and resource evidence on the supported Ubuntu runner.

Validation remains `Revise / WAITING_HUMAN`; every conjunctive V00 exit condition
remains unmet or unverified. F01 adds no role, learner, mastery, evidence, or
readiness state and does not unlock V01.

## Last completed action

Isolated Windows-only `WinDLL` and `get_last_error` access behind a typed,
runtime-checked private adapter, preserved native error-code provenance, and
added delegation, explicit-unavailability, and errno regression coverage.

## Exact next action

Commit and push the verified two-file ctypes portability repair so exact-revision
Ubuntu CI can rerun.

## Changed files

This run changes the private supervisor FFI boundary and its tests, then updates
the F01 ExecPlan, inventory, controller goal, state, run log, and this checkpoint.
No dependency, lockfile, public schema, product behavior, or V00/V01 artifact
changes. The externally committed, unrelated 66,312,302-byte
`ai-learning-platform.7z` remains tracked but untouched.

## Validation results

The user-supplied exact CI log records 10 strict-mypy errors and exit 1 at the
pushed revision. After repair, native, `--platform linux`, and `--platform
win32` strict mypy each pass 23 files. Ruff format and lint pass. Eighty-two
focused supervisor/smoke tests pass; the final API suite passes 127 tests at 97%
line and branch coverage. Locked sync and both canonical contract checks pass.

The exact Windows root smoke reached API liveness in 2,265 ms, completed all
assertions in 7,742 ms, shut down in 204 ms, and left no listener on ports 3000
or 8000. Independent verification also reproduced 38 supervisor tests including
three real Windows lifecycle cases, native DLL/error access, the three mypy
targets, Ruff, unchanged constitutional boundaries, and secret/diff hygiene; it
found no code defect. `git diff --check` passes.

## Unresolved findings

No successful Ubuntu CI run exists for the repaired exact revision, so Linux
process-count/resident-memory and final workflow conclusions are missing. The
GitHub CLI is unavailable locally and the connector exposes no push-triggered
run for this commit, so the user-supplied failure log is the remote source. The
tracked 66.3 MB archive adds repository and CI-checkout cost and remains outside
the authorized repair scope. Four protected V00 Markdown working copies remain
mixed-EOL locally while their index blobs are LF and they have no content diff;
they were preserved rather than rewritten during this API repair.

## External blockers

F01 requires publication and an exact-revision supported-Ubuntu CI rerun. V00
separately still requires two qualified practitioners, a real 20-50-adult
recruitment channel, and privacy-safe confirmations.

## Human decisions required

Commit/push authorization for the two-file repair is required before
exact-revision CI can rerun. The V00 demand-sufficiency,
practitioner-qualification, and expected-cost rules also remain unapproved.

## Rollback point

`25994d2` on `automation/v00-phase-loop`; this run performed no commit or push.

## Another run may proceed automatically

No. Publish this verified repair and obtain remote CI evidence first. Do not
begin another phase or V01.
