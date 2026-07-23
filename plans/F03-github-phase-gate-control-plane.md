# ExecPlan: F03 GitHub Phase-Gate Control Plane

**Phase:** `F03 - GitHub Phase-Gate Control Plane`
**Class:** Technical foundation
**Status:** `PASSED / Continue`. Implementation revision
`fe49b609767e27d52fae999c229502ed98866dff` passed exact GitHub Actions push
run `29528587173` and pull-request run `29528587169`. Acceptance revision
`c2938f2d0496088ea117acf387424530ad0b4c59` passed its own exact push run
`29577006084` and pull-request run `29577007722`; all five required jobs
succeeded in both runs. F03 is durably accepted.
**Decision owner:** Primary agent under the autonomous-decision rule
**Integration surface:** Pull request #1 on `automation/v00-phase-loop`
**Validation lane:** `V00` remains `WAITING_EXTERNAL / Revise`; `V01` remains locked.

## Objective

Create a deterministic, fail-closed GitHub-hosted acceptance controller that
validates the exact checked-out revision, derives both lane projections from
versioned repository evidence, and makes internally decidable technical phase
acceptance independent of chat approval. F03 adds no product runtime or
deployment behavior.

## Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| F00-F02 passed | F02 controller revision `8963101805d6f29f4701c91764b5563f07ff07c8`, Actions run `29511515229` | Passed |
| Persistent integration PR exists | Pull request #1 | Passed |
| Durable steering authorizes autonomous technical acceptance | Latest durable pull-request steering comment | Passed |
| The control-plane contract is authoritative | GitHub issue #2 | Passed |
| Deployment remains outside F03 | GitHub issue #3 reserves later F04 | Passed |
| Current three-check baseline is green but incomplete | Revision `5b19455034583da0d0ec40c82edf70423b93b2df`, run `29514959237` | Passed as entry evidence only |

The baseline run is not F03 acceptance evidence because it has only API
quality, Web quality, and Runtime smoke. Both the implementation and separate
acceptance-state revisions must pass all five required checks.

## Scope

F03 includes one bounded control-plane implementation:

1. a versioned machine-readable controller policy;
2. a deterministic, non-mutating repository validator;
3. a deterministic GitHub Step Summary projection;
4. exact-head checkout and validation in all CI jobs;
5. `Phase gate` and `Gate projection` jobs;
6. adversarial tests for every fail-closed invariant;
7. the implementation-revision, acceptance-state-revision, and exact-check loop;
8. an explicit operating-contract update in `AGENTS.md`.

The parent agent is the only writer. `architecture_guardian` and
`roadmap_gate_reviewer` are bounded read-only reviewers. A separate
`verification_reviewer` reviews the completed implementation before it is
published.

## Authoritative Inputs

The controller reads only:

- `plans/autonomous-loop/controller-policy.json` for versioned vocabulary,
  immutable blocker classes, claim prerequisites, exact-head rules, file-size
  bounds, and the five required check names;
- `specs/roadmap.md` for phase IDs, names, lanes, order, and dependencies;
- `plans/autonomous-loop/state.json` for the active controller projection;
- `plans/implementation-inventory.json` for implementation and phase evidence;
- `.github/workflows/ci.yml` for the exact workflow contract; and
- files named by the state's authoritative SHA-256 map.

The policy deliberately does not duplicate roadmap phase purposes or the
dependency graph. Unknown policy fields, schema versions, status values,
dependency syntax, blockers, claims, effects, or check names fail closed.

## Controller Rules

The validator performs these checks before it emits any projection:

1. bound every input by path, size, UTF-8, and strict duplicate-key JSON rules;
2. require the supplied expected SHA to equal the checked-out 40-hex Git HEAD and reject any tracked or untracked working-tree drift;
3. parse unique roadmap phases and the approved dependency forms: `None`,
   explicit backticked IDs, a same-lane `A through B` range, or
   `All preceding phases`;
4. reject unknown, forward, self, cross-lane, malformed, or unsatisfied
   dependencies;
5. require roadmap and inventory IDs, names, lanes, order, statuses, entries,
   gate decisions, evidence, blockers, claims, and effects to agree;
6. prevent V01 or later validation progress while V00 is not passed, and V02+
   progress while V01 is not passed;
7. require every passed phase to have `Continue`, passed entry evidence,
   implementation files, tests, no missing outputs, and passed dependencies;
8. prevent a foundation phase from depending on, satisfying, unlocking,
   weakening, or claiming a validation outcome;
9. bind the canonical V00 blockers to their immutable external class, permit
   only technical foundation blockers, and reject conversion into a human-
   approval wait;
10. validate every claim prerequisite against a unique validation phase and
    reject unsupported target, profile, beta-entry, external-readiness, or
    complete-role-readiness claims;
11. require state/inventory timestamp, phase, lane, status, gate, verified-head,
    and authoritative-file hashes to agree; and
12. require the verified predecessor to be an ancestor of the exact checkout; and
13. require the exact implementation-transition pending condition, missing
    outputs, and complete blocker set before projecting autonomous eligibility.

State staleness is structural, not wall-clock based. Identical immutable commits
therefore remain reproducible, while hash drift, schema drift, phase mismatch,
timestamp disagreement, or a non-ancestor verified revision fails.

## Deterministic Projection

Projection occurs only after full validation. Its versioned JSON and Step
Summary contain:

- the exact commit SHA;
- validation and foundation phase, status, and gate;
- the passed prerequisite chain;
- external, technical, and human-decision blocker IDs;
- one fixed next-action kind, phase, and reason code; and
- autonomous-acceptance eligibility with fixed reason codes.

The projection contains no timestamps, durations, evidence prose, URLs,
exceptions, environment values, secrets, learner data, or unordered sets.
Repeated runs from identical files, SHA, and upstream results are byte-identical.
The controller may append the summary only to an explicitly supplied path
outside the repository.

## GitHub Workflow Contract

All five jobs explicitly check out:

```text
github.event.pull_request.head.sha || github.sha
```

with credentials persistence disabled. The two controller jobs have exact names:

```text
Phase gate
Gate projection
```

`Phase gate` runs in parallel with API and web quality. `Gate projection` uses
`always()`, waits for API quality, Web quality, Runtime smoke, and Phase gate,
revalidates the repository independently, renders the exact projection, and
fails unless every upstream result is `success`. Pending, failed, cancelled, or
skipped results cannot be accepted. All actions remain full-SHA pinned and the
workflow retains read-only contents permission, bounded timeouts, no secrets,
no artifact trust boundary, and no repository or pull-request mutation.

## Adversarial Test Strategy

The test suite starts from a known-good repository fixture, copies bounded
controller inputs, mutates one invariant at a time, and refreshes unrelated
hash evidence only when needed to reach the intended rule. It proves failure for:

- malformed, duplicate-key, oversized, escaped-path, or unsupported policy and
  JSON inputs;
- duplicate, unknown, malformed, forward, cross-lane, cyclic, or unsatisfied
  dependencies;
- V00/V01 lock violations and premature horizon progress;
- state/inventory phase, status, gate, timestamp, verified-head, or hash drift;
- a passed phase with failed or pending entry evidence, missing outputs,
  missing implementation evidence, or a non-Continue decision;
- foundation effects on validation and unsupported product/readiness claims;
- coordinated external-blocker reclassification and nontechnical foundation blockers;
- previous-head validation, a mismatched expected SHA, and dirty working-tree bytes;
- missing, renamed, duplicated, elevated, credentialed, bypassed, hard-coded-
  result, or merge-ref workflow jobs;
- missing, pending, failed, cancelled, or skipped upstream results; and
- nondeterministic or repository-mutating projection behavior.

The complete API suite must remain at or above 95% branch-aware coverage. Web
quality and the real cross-process runtime smoke remain mandatory even though
F03 changes no web or application runtime code.

## Local Validation Evidence

All results below were executed from the implementation worktree before
independent review:

| Gate | Result | Duration or observation |
| --- | --- | --- |
| Locked API synchronization and both generated-contract drift checks | Passed | 39 packages resolved; 38 checked |
| Ruff format and lint | Passed | 30 files |
| Strict mypy | Passed natively and for Linux and Win32 targets | 30 files per target |
| Adversarial controller suite | 134 passed | 9.80 seconds; controller module 97% branch-aware coverage in the full suite |
| Complete API suite | 402 passed | 26.69 seconds; 97% overall branch-aware coverage; `smoke.py` 95% |
| Locked web install and audit | Passed | 384 packages; zero vulnerabilities |
| Web lint, strict typecheck, unit tests, build, and confidentiality | Passed | 97 tests in 8 files; compile 1.358 seconds; typecheck 1.877 seconds; 10 files / 629,565 bytes; complete web gate 43.854 seconds |
| Real cross-process runtime smoke | Passed twice | 48 events; 21 correlations; 4 concurrent requests; 12,638 diagnostic bytes; 14,223-14,224 captured bytes; 51-102 ms shutdown; about 7 seconds per command; both ports closed |
| Dirty-worktree exact-head adversarial check | Failed closed as designed | `worktree_not_exact_head` at entry SHA `5b19455034583da0d0ec40c82edf70423b93b2df`; clean exact-head Phase gate and Gate projection are deferred until the implementation commit |
| Initial controller resource observation | Informational | Before the final clean-worktree hardening, 20 validation/projection iterations averaged 173.578 ms, peaked at 1,392,192 traced Python heap bytes, and emitted 853 bytes; exact CI duration is recorded after push |

Independent verification reproduced the 133 targeted and 383 full API tests,
Ruff, strict mypy, hashes, JSON, and diff checks. It found and drove repairs for
unknown explicit dependency IDs, hard-coded upstream check sources, coordinated
external-to-human reclassification, incomplete transition evidence, ignored
nontechnical blockers, dirty-worktree SHA labeling, invalid claim prerequisites,
and workflow execution bypasses. No material finding remained open on that implementation snapshot. The
canonical-LF repair below was then independently accepted before its exact
GitHub run.

The first sandboxed `npm ci` attempt was denied by the Windows process sandbox
with `spawn EPERM`; the required escalated rerun completed successfully. This is
an execution-environment permission observation, not an application or lockfile
failure. No dependency or lockfile changed. Generated `.coverage`, `.next`, and
dependency-install artifacts are ignored and are not part of the bounded diff.

## Implementation Attempt 1 and Repair

Implementation attempt `9746ceb16a3bbfc1e95a8bfadae6224fe77dfe21`
passed clean local exact-head Phase gate and Gate projection, then was rejected by
exact GitHub Actions run `29521143904`:

| Job | Job ID | Conclusion |
| --- | ---: | --- |
| API quality | `87698239491` | Failure |
| Web quality | `87698239481` | Success |
| Runtime smoke | `87698419979` | Skipped |
| Phase gate | `87698239511` | Failure |
| Gate projection | `87698419129` | Failure |

The Phase gate log reported `state_hash_mismatch`; API reproduced the same root
cause across 32 controller tests. Two V00 Markdown files are LF in Git but are
transparently CRLF-converted in the clean Windows worktree, so hashes generated
from raw Windows bytes could not match the Linux checkout. The repair hashes
all authoritative text after CRLF-to-LF canonicalization, retains the clean-
worktree and exact-SHA checks, and adds a regression that validates identical LF
and CRLF checkouts. Independent follow-up verification reproduced LF success,
CRLF success, and rejection of a real content mutation with
`state_hash_mismatch`. It passed 134 targeted tests in 9.43 seconds and 384
full API tests in 26.50 seconds at 97% branch-aware coverage, plus Ruff, native,
Linux, and Win32 strict mypy, both generated-contract checks, JSON, hashes, and
diff checks. The failed run is not acceptance evidence. A new exact five-check
implementation revision remains required.

## Implementation Attempt 2 and Runtime Repair

Canonical-hash repair revision `34d5de2b5af15ec39e09b0f91ed5d358020dcfed`
was rejected by exact run `29523254781`:

| Job | Job ID | Conclusion |
| --- | ---: | --- |
| API quality | `87705173886` | Success |
| Web quality | `87705173871` | Success |
| Runtime smoke | `87705355479` | Failure |
| Phase gate | `87705173912` | Success |
| Gate projection | `87705481759` | Failure |

The Linux runtime captured a nondeterministic loopback or documentation URL from
framework-owned Next.js stderr. The accepted F02 outer validator correctly
rejected it because every captured byte remains untrusted. This repair does not
relax that validator. Real diagnostic-service stderr is now piped through a
bounded child-side router before it enters the outer capture: structured JSON,
inner-proof, and diagnostic-marker candidates are forwarded unchanged;
confidential canaries, oversized lines, I/O failures, and premature pipe closure
fail safely; ordinary framework-owned lines become fixed allowlisted
`process.log` events. The outer capture remains byte-bounded and scans every
resulting byte for all confidential and forbidden categories. The runtime suite
passes 126 tests, including full-capture rejection and adversarial router
failures, and two real local smokes pass with 48 events and 21 correlations. The
full 402-test API replay passes at 97% overall coverage with `smoke.py` at 95%,
along with Ruff, native/Linux/Win32 strict mypy, contracts, canonical hashes,
JSON, and diff checks. Independent follow-up verification returned `ACCEPT`
with no material finding. It independently reproduced 126 runtime, 47
supervisor, 134 controller, and 402 full API tests at 97% overall coverage with
`smoke.py` at 95%; Ruff, all three mypy targets, both contracts, 24 hashes,
and two real smokes also passed. A new exact five-check implementation revision
is now required.

## Implementation Attempt 3 and Acceptance

Implementation revision `fe49b609767e27d52fae999c229502ed98866dff` (the
corrected pre-capture runtime-log repair, independently accepted with no
material finding) was pushed to `automation/v00-phase-loop`. Two exact-head
GitHub Actions runs completed against that exact SHA:

| Job | Push run `29528587173` | Pull-request run `29528587169` |
| --- | ---: | ---: |
| API quality | `87723081841` success | `87723082409` success |
| Web quality | `87723081644` success | `87723082444` success |
| Runtime smoke | `87723264188` success | `87723243300` success |
| Phase gate | `87723082122` success | `87723082447` success |
| Gate projection | `87723443710` success | `87723382365` success |

All ten job executions across both runs succeeded on the exact implementation
SHA. This satisfies the implementation-side exit condition of the F03
acceptance sequence. This ExecPlan revision is the separate acceptance-state
commit required by Step 5 of the sequence below: it records the implementation
evidence and sets F03 to `PASSED / Continue`. That acceptance revision is
`c2938f2d0496088ea117acf387424530ad0b4c59`; its exact push run `29577006084`
and pull-request run `29577007722` each completed all five required jobs with
`success`, completing the F03 acceptance sequence.

## Implementation Files

- `plans/autonomous-loop/controller-policy.json`
- `apps/api/src/ai_learning_platform_api/automation/__init__.py`
- `apps/api/src/ai_learning_platform_api/automation/phase_gate.py`
- `scripts/phase_gate.py`
- `apps/api/tests/test_phase_gate.py`
- `apps/api/src/ai_learning_platform_api/development/smoke.py`
- `apps/api/src/ai_learning_platform_api/development/supervisor.py`
- `apps/api/tests/test_runtime_smoke.py`
- `apps/api/tests/test_dev_supervisor.py`
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `specs/roadmap.md`
- controller state, checkpoint, run log, and implementation inventory

No application dependency or lockfile is changed.

## Acceptance Sequence

1. Complete local API, web, runtime, phase-gate, and projection validation.
2. Obtain independent read-only verification and repair every confirmed finding.
3. Commit and push the bounded F03 implementation revision.
4. Require that exact SHA's API quality, Web quality, Runtime smoke, Phase gate,
   and Gate projection jobs to complete successfully.
5. Record the exact implementation SHA, workflow run ID, and job IDs in a
   separate acceptance-state commit that updates this plan, controller state,
   checkpoint, run log, and inventory.
6. Push the acceptance-state revision and require its own exact five jobs to
   pass.
7. Record both immutable revisions and both workflow runs in pull request #1.
8. Stop before F04.

An acceptance commit cannot contain its own future workflow run IDs without a
self-referential third revision. Its successful exact-head run is therefore
recorded as durable PR evidence after the run completes. Earlier-head success
never accepts a newer revision.

## Performance and Resources

The controller uses only Python's standard library and reads bounded local
files. It starts no service, process supervisor, database, network client, or
model call. Record validator and projection duration and peak memory locally,
then record the five-job GitHub run duration. Added CI cost is two short Python
jobs; Gate projection intentionally waits for the existing dependent chain so
its success is the final fail-closed projection.

## Data, Privacy, Security, and Compatibility

F03 processes repository metadata only. It adds no database, migration,
learner or role record, credential, secret, object, external telemetry, LLM
request, deployment state, or retained runtime artifact. Workflow permissions
remain `contents: read`; checkout credentials are not persisted; no
`pull_request_target`, write token, issue mutation, merge, deployment, or
untrusted shell interpolation is introduced. Existing API, web, OpenAPI,
diagnostic, and runtime contracts remain compatible.

## Rollback

Revert the bounded F03 implementation and workflow changes together. The
accepted F00-F02 application runtime remains operational under the prior three
checks, but autonomous phase acceptance returns to unavailable. No data or
external-resource rollback is required.

## Non-Goals

- Database, persistence, authentication, tenancy, learner or role models.
- Competency, curriculum, assessment, mastery, simulation, or readiness logic.
- LLM calls, product claims, V00 evidence, V01 unlock, or validation acceptance.
- Dockerfiles, containers, deployment, Vercel configuration, provider selection,
  custom domains, production topology, or measured deployment cost.
- F04 definition or implementation in this invocation.

## Gate Decision Rules

- `Continue`: the implementation revision and separate acceptance-state
  revision each pass all five exact-head jobs after independent verification.
- `Revise`: any policy, controller, test, workflow, documentation, exact-head,
  or job-result invariant is repairably incomplete or failing.
- `Narrow`: retain only a smaller deterministic controller if the projection
  surface cannot be made fail closed without expanding authority.
- `Stop`: acceptance would require secrets, write authority, deployment,
  validation-gate weakening, fabricated evidence, or a human approval that the
  autonomous-decision rule forbids.

## Next Boundary

After both F03 revisions pass, stop. The only next eligible action is:

```text
Formally define and implement F04 — Vercel deployment baseline from GitHub issue #3.
```

F04 remains separate and must reconcile Vercel with the managed-PaaS technical
constitution before any deployment configuration is added.
