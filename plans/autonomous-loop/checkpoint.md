# Autonomous Loop Checkpoint

## Current phase and gate

Foundation phases F00-F02 are `PASSED / Continue`. F02 controller revision
`8963101805d6f29f4701c91764b5563f07ff07c8` passed exact GitHub Actions run
`29511515229`.

`F03 - GitHub Phase-Gate Control Plane` is `PASSED / Continue`. Pull request #1
is the persistent integration and evidence PR. Implementation revision
`fe49b609767e27d52fae999c229502ed98866dff` passed exact GitHub Actions push run
`29528587173` and pull-request run `29528587169`: API quality, Web quality,
Runtime smoke, Phase gate, and Gate projection all succeeded on the exact SHA
in both runs (ten job executions total). This checkpoint revision is the
separate acceptance-state commit; its own exact five-job GitHub run is the
final confirmation step and will be recorded as durable PR evidence once
observed.

The validation lane remains `V00 - Candidate Role Evidence`,
`WAITING_EXTERNAL / Revise`; V01 remains locked. No human review is pending.

## Durable steering and issue boundary

The latest durable steering comment on pull request #1 makes GitHub the source,
CI, exact-revision, and integration control plane; requires separate
implementation and acceptance-state revisions; and rejects previous-head,
pending, failed, skipped, cancelled, or stale checks. GitHub issue #2 is the
complete F03 contract. GitHub issue #3 reserves the later F04 Vercel deployment
baseline; it becomes eligible only after this acceptance-state revision's own
exact five-job GitHub run is confirmed, and remains out of scope for this
invocation regardless.

The obsolete container/preview definition at the entry head has been replaced.
F03 adds no deployment or Vercel configuration. Any preview created by an
already-connected provider is an unverified side effect, not phase evidence.

## Agent reconciliation

`architecture_guardian` and `roadmap_gate_reviewer` independently identified the
same decisive conflict: local F03 deployment text contradicted issue #2 and the
PR steering. Both recommended deriving dependencies from the roadmap rather
than duplicating them in policy, fail-closed exact-head validation, explicit
lane isolation, and separate implementation and acceptance revisions.

Architecture review additionally recommended immutable blocker classes,
structured claim/effect rules, full-SHA-pinned read-only workflow actions, and a
final projection job that revalidates repository state and upstream results.
Roadmap review clarified that Q2-Q4 are horizons, not autonomously progressed
phases, and that an acceptance commit cannot embed its own future run IDs. The
integrated implementation adopts these points and records the acceptance run in
PR evidence after it completes.

`verification_reviewer` independently reproduced the targeted and full API
gates. It found material fail-closed gaps in unknown explicit dependency IDs,
upstream-result source binding, coordinated external-blocker reclassification,
transition missing-output and blocker completeness, dirty-worktree SHA labeling,
claim prerequisites, and workflow execution bypasses. All confirmed findings
were repaired. Its final rerun passed 133 targeted tests, 383 full API tests at
97% branch-aware coverage, Ruff, strict mypy, authoritative hashes, JSON, and
diff checks with no open material finding.

## Implemented controller

The bounded F03 implementation contains:

- `plans/autonomous-loop/controller-policy.json`, a versioned policy for status,
  gate, blocker, claim, exact-head, check-name, and bounded-input rules;
- `ai_learning_platform_api.automation.phase_gate`, a standard-library,
  non-mutating validator and deterministic projector;
- a thin repository-root `scripts/phase_gate.py` entrypoint;
- adversarial tests that mutate one repository invariant at a time;
- explicit exact-head checkout with non-persisted credentials in all CI jobs;
- `Phase gate` and final fail-closed `Gate projection` jobs; and
- the exact implementation/acceptance loop in `AGENTS.md`.

The roadmap remains the sole phase/dependency source. The controller rejects
malformed policy or JSON, dependency and lane violations, V00/V01 lock bypass,
state/inventory/hash drift, missing passed evidence, external-to-human blocker
conversion, unsupported readiness claims, privileged or merge-ref workflow
drift, prior-head validation, and non-success upstream jobs.

## Current evidence state

The canonical-LF repair was independently accepted. For the subsequent runtime
repair, the adversarial controller suite passed 134 tests in 9.80 seconds; the
complete API suite passed 402 tests in 26.69 seconds at 97% branch-aware
coverage with `smoke.py` at 95%; and Ruff plus native, Linux, and Win32 strict
mypy passed across 30 files. The web lane passed locked install with zero
vulnerabilities, lint, strict typecheck, all 97 tests, production build, and a
10-file/629,565-byte confidentiality scan. Two corrected real smokes passed in
about 7 seconds each with 48 events, 21 correlations, 4 concurrent requests,
12,638 diagnostic bytes, 14,223-14,224 captured bytes, 51-102 ms shutdown, and
both ports closed.

The hardened CLI intentionally rejects the dirty implementation worktree with
`worktree_not_exact_head`; clean exact-head Phase gate and Gate projection runs
are deferred until the implementation commit exists. A pre-hardening
20-iteration observation averaged 173.578 ms, peaked at 1,392,192 traced Python
heap bytes, and emitted an 853-byte projection. Exact controller and CI duration
will be refreshed from the clean commit and GitHub run. The parent will now
publish one bounded implementation revision and repair every failed exact job
without user approval.

Implementation attempt `9746ceb16a3bbfc1e95a8bfadae6224fe77dfe21`
passed the clean local controller checks but exact GitHub run `29521143904`
failed closed. Web quality (`87698239481`) succeeded; API quality
(`87698239491`), Phase gate (`87698239511`), and Gate projection
(`87698419129`) failed; Runtime smoke (`87698419979`) was skipped. Raw hashes
for two V00 Markdown files differed between the transparently CRLF-converted
Windows worktree and Linux LF checkout. The repair canonicalizes authoritative
text to LF before hashing and adds a checkout-line-ending regression. The failed
run is repair evidence only. Follow-up verification independently reproduced
LF success, CRLF success, and rejection of a real content mutation with
`state_hash_mismatch`; it passed 134 targeted and 384 full API tests at 97%
branch-aware coverage plus Ruff, strict mypy for all three platform targets,
contracts, hashes, JSON, and diff checks. The repair is accepted for a new
implementation revision.

Canonical-hash repair revision `34d5de2b5af15ec39e09b0f91ed5d358020dcfed`
was then rejected by exact run `29523254781`: API quality
(`87705173886`), Web quality (`87705173871`), and Phase gate
(`87705173912`) succeeded; Runtime smoke (`87705355479`) failed on a
framework-owned raw URL in the private Linux stderr capture; Gate projection
(`87705481759`) failed closed. The repair preserves F02's full-capture scan
unchanged and routes real service stderr before capture. Structured JSON,
inner-proof, and marker candidates remain byte-exact; confidential canaries,
oversized lines, I/O failures, and premature pipe closure fail safely; only
ordinary framework-owned lines become fixed allowlisted `process.log` events.
The 126 runtime tests, two real local smokes, and 402-test full API replay pass
at 97% overall coverage with `smoke.py` at 95%. Ruff, native/Linux/Win32
strict mypy, contracts, canonical hashes, JSON, and diff checks pass.
Independent follow-up verification returned `ACCEPT` with no material finding
after reproducing 126 runtime, 47 supervisor, 134 controller, and 402 full API
tests at 97% overall coverage with `smoke.py` at 95%, plus both real smokes and
all static gates. Only the exact implementation and acceptance-revision GitHub
checks remain pending.

Only after that exact implementation revision passes will a separate commit
project F03 as `PASSED / Continue` and record the implementation SHA, run, and
job IDs. That acceptance-state commit must then pass its own exact five jobs.
Its future run IDs will be recorded durably in pull request #1, avoiding a
self-referential third repository commit.

## Lane blockers and claims

V00 still lacks four external blocker classes:

- `v00.symmetric_demand`;
- `v00.practitioner_confirmations`;
- `v00.recruitment_channel`; and
- `v00.measured_cost`.

They cannot be fabricated or converted into a human technical-approval wait.
F03 has no validation effect and makes no target, product, beta-entry, role-
readiness, or complete-role-readiness claim.

## Data, performance, and compatibility

F03 reads bounded repository metadata only and uses no new dependency. It adds
no database, migration, learner data, role data, secret, service, external
request, LLM call, artifact upload, deployment, or product runtime path. The
API, web, OpenAPI, and diagnostic event contracts remain unchanged. The
existing F02 outer capture remains fully byte-bounded and applies its
confidential and forbidden-category scan to every captured byte. A bounded
child-side router maps only ordinary framework-owned stderr before that capture
while forwarding all structured, proof, and marker candidates unchanged.
Controller and exact GitHub durations are recorded per implementation attempt.

## Exact next action

Push this acceptance-state revision and require its own exact five GitHub jobs
(API quality, Web quality, Runtime smoke, Phase gate, Gate projection) to pass
on its exact SHA. Repair any failure with a bounded new revision and repeat
until they pass. Once confirmed, record both the implementation revision
(`fe49b609767e27d52fae999c229502ed98866dff`) and this acceptance revision, with
both accepted workflow runs, as durable evidence in pull request #1, and stop
before F04.
