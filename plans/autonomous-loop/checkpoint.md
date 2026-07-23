# Autonomous Loop Checkpoint

## Run 27 current phase and gate

F04 remains active and `FAILED_RETRYABLE / Revise`. This bounded repair started
from clean branch `automation/f04-vercel-deployment-baseline` at exact SHA
`4b4d1944ee34ded8921c88222902f0de0be1fb53`, with pull request #5 open and
mergeable. Only `f04.deployed_page_verification` was in scope.

The implementation chain culminated in exact revision
`4e6770a1e1dcf2938f224c93c0701bae0e8e5f4c`. Its dedicated, push-only workflow
joined the exact GitHub Vercel status and deployment records to canonical Vercel
deployment `dpl_6U2FrqVs6paxCpnN7EaCd6dLMDTA`, exact branch/project metadata,
and `READY` preview state before accepting the protected page. The immutable
hostname returned HTTP 200 with no redirect or authentication response, one
accessible `role=status` API-unavailable state, and no loopback origin, health
path, trace context, or shared confidential marker across 8,402 HTML bytes and
seven browser assets totaling 629,464 bytes.

GitHub Actions run `29865352967`, job `88752059522`, passed on that exact SHA and
published sanitized artifact `8508962218`. The artifact's SHA-256 is
`53e23522c69970a8011a3ecb9a0b7a61cfa598551531045ec63f7836b16f6f5b`; its
committed projection is
`plans/F04-vercel-deployed-page-verification-evidence.json`. Bounded discovery
completed in three attempts and 14,001 ms. Exact push run `29865352971` also
passed API quality, Web quality, Runtime smoke, Phase gate, and Gate projection.

Local validation passed the 40-test focused verifier suite, all 137 web tests,
web lint, strict typecheck, production build, confidentiality scan, all 426 API
tests at 97% coverage, Ruff, strict mypy, canonical generation checks, the
48-event root runtime smoke, controller tests, phase validation, gate projection,
and repository secret checks. Independent read-only review found one repeatable
PowerShell package-script invocation defect. The runbook now requires the
verified `npm.cmd` shim on PowerShell and keeps the ordinary `npm run` form for
Bash/CI; the focused rereview returned `PASS / Continue` with no material
finding.

The first evidence/state revision
`cde7940a308ba81324713d1763a56908922b8886` deployed successfully, but exact
workflow run `29866121231` failed after 14 seconds because the exact GitHub
deployment was visible before its deployment-status list propagated. The
verifier now treats an empty status list as retryable within its unchanged
five-minute bounded poll while continuing to reject malformed, ambiguous, or
terminally unsuccessful status responses. The focused suite passes 41 tests;
all 138 web tests, lint, strict typecheck, production build, and confidentiality
scan pass; and independent focused rereview returned `PASS / Continue`. The
repair revision's exact remote checks remain the publication gate.

During credential setup, two superseded Vercel automation-bypass values were
exposed only in ephemeral local tool output, treated as compromised, and revoked
immediately. Neither value entered Git, GitHub Actions logs, artifacts, pull
requests, or issues. A rejected personal-scope Vercel token was also revoked.
The final bypass is unexposed, and the dedicated verifier token is short-lived
through 2026-07-22. No credential, cookie, raw authorization header, full HTML,
or temporary share URL is committed.

Only `f04.deployed_page_verification` is resolved in this record. The three
remaining F04 blockers are:

- `f04.build_reproducibility`;
- `f04.resource_measurements`; and
- `f04.repository_payload_hygiene`.

V00 remains `WAITING_EXTERNAL / Revise` with its four external inputs; V01
remains locked. No F04 acceptance-state revision is created. The only next
eligible blocker is `f04.build_reproducibility`.

## Prior Run 26 checkpoint

F04 remains active and `FAILED_RETRYABLE / Revise`. Run 26 started from clean
branch `automation/f04-vercel-deployment-baseline` at exact SHA
`ceaf60d2ce5adf826b8268c32e513569a35eeb0c`; pull request #5 was open and
mergeable, both exact GitHub workflow runs passed all five required jobs, and
Vercel preview `dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z` was `READY` for that SHA.

The bounded repair resolved only `f04.rollback_reversion`. Dedicated alias
`f04-reversion-proof-web.vercel.app` followed the required B-to-A-to-B sequence:

- B: `dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z` at
  `ceaf60d2ce5adf826b8268c32e513569a35eeb0c`;
- A: `dpl_64G3A2Zim5iWcQ2YzrQnW9runPii` at
  `ca08301b46e49945a805f20a07866a931a8e81e0`; and
- restored B: `dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z` at
  `ceaf60d2ce5adf826b8268c32e513569a35eeb0c`.

Vercel's supported alias REST response identified the exact prior deployment on
both moves. After every assignment, bounded polling verified exclusive alias
ownership, expected project, `READY` preview target, and exact Git SHA before an
authenticated `vercel curl` request was accepted. All three requests returned
HTTP 200 application HTML with no redirect and the accessible API-unavailable
state. Loopback origins, the health path, trace identifiers, and confidential
diagnostic markers were absent. The Git-managed branch alias and production
aliases were unchanged. The alias remains on B, and sanitized evidence is at
`plans/F04-vercel-alias-reversion-evidence.json`.

The evidence contract passed all 21 focused tests, including the required
fail-closed mutations, and all 158 controller tests passed. The complete API
quality gate passed 426 tests at 97% coverage with canonical generation, Ruff,
and strict mypy; web lint, strict typecheck, all 97 tests, production build, and
browser confidentiality scan passed; and the root runtime smoke passed with 48
events, 21 correlations, four concurrent requests, bounded diagnostics, and
clean shutdown. Exact clean-revision phase-gate and projection evidence remains
the publication gate for this bounded revision.

Independent final read-only review returned `ACCEPT` with no material findings
after rechecking the live final alias and isolation state, exact deployment/SHA
chain, HTTP response, evidence schemas, all authoritative hashes, 158 controller
tests, and the 426-test API gate. This disposition applies only to the bounded
rollback-reversion repair; F04 remains `Revise`.

The four remaining F04 blockers are:

- `f04.deployed_page_verification`;
- `f04.build_reproducibility`;
- `f04.resource_measurements`; and
- `f04.repository_payload_hygiene`.

V00 remains `WAITING_EXTERNAL / Revise` with its four external inputs; V01
remains locked. No F04 acceptance-state revision is created. The only next
eligible blocker is `f04.deployed_page_verification`.

## Prior Run 25 checkpoint

Foundation phases F00-F03 are durably `PASSED / Continue`. F03 implementation
revision `fe49b609767e27d52fae999c229502ed98866dff` passed exact push/PR runs
`29528587173` and `29528587169`; acceptance revision
`c2938f2d0496088ea117acf387424530ad0b4c59` passed exact runs `29577006084` and
`29577007722`.

F04 is active and `FAILED_RETRYABLE / Revise`. This run started from clean branch
`automation/f04-vercel-deployment-baseline` at exact SHA
`ca08301b46e49945a805f20a07866a931a8e81e0`. Pull request #5 is open and
mergeable. Exact run `29616557723` passed API quality, Web quality, Runtime smoke,
Phase gate, and Gate projection; Vercel deployment
`dpl_64G3A2Zim5iWcQ2YzrQnW9runPii` is `READY` and linked to that SHA.

Those green checks are entry evidence for this repair, not F04 acceptance.

The validation lane remains `V00 - Candidate Role Evidence`,
`WAITING_EXTERNAL / Revise`; V01 remains locked.

## Confirmed F04 defects

- The controller trusted a manually retargeted active phase, required F04 as its
  own future boundary, and emitted `DEFINE_F04` after F04 was marked passed.
- Current Markdown and JSON records retained stale F03-pending, old branch, and
  pre-acceptance SHA claims.
- `vercel rollback` returned HTTP 422 for a preview target; that rejected command
  and independently reachable preview URLs do not demonstrate traffic reversion.
- The protected deployed page had only user visual confirmation. An authenticated
  live diagnostic rendered the HTTP 200 API-unavailable state with `role=status`,
  but no committed exact-deployment verifier exists and unauthenticated redirects
  can still be mistaken for HTTP success.
- Version-controlled Vercel configuration, compatible Vercel Node/npm install,
  deployed confidentiality proof, and required resource/cost measurements remain
  incomplete.
- The unrelated `ai-learning-platform.7z` was verified at 66,312,302 bytes and
  removed from the current tree without history rewriting. The exact root ignore
  rule prevents recurrence; exact-head checks remain the publication gate.

## Bounded repair in this revision

This revision changes only controller/frontier logic and authoritative state:

- derive each lane's active phase from roadmap order and inventory status;
- derive the foundation successor from roadmap order, with an explicit nullable
  no-successor boundary instead of a phase self-loop;
- use generic controller transition blockers and `automation/**` workflow/policy
  matching;
- clarify that rollback requires traffic movement and restored final state;
- return F04 to `FAILED_RETRYABLE / Revise` with explicit missing outputs; and
- synchronize the goal, checkpoint, run log, ExecPlan, roadmap, inventories, and
  current branch/SHA evidence.

No deployment alias is changed, no production deployment is created, no archive
is removed, and no product or domain behavior is added.

## Independent review

Read-only mission, roadmap, architecture, and controller reviewers unanimously
returned `Revise`. They confirmed the self-loop, stale state, invalid rollback
claim, missing committed deployment contract, missing deployed-page proof, and
missing resource observations. They also confirmed that the web-only role-neutral
boundary, V00 external blockers, V01 lock, and false readiness claims remain
intact.

## Validation state

Local affected gates pass: 137 controller tests; canonical generation, Ruff,
strict mypy, and 405 API tests at 97% total coverage; web clean install, lint,
strict typecheck, 97 tests, production build, and browser confidentiality scan;
and the final public runtime smoke with exactly 48 diagnostic events. One earlier
smoke attempt failed on event volume, but its suppressed child evidence prevents
an exact diagnosis; a bounded direct-child rerun and the public rerun both passed,
and no smoke code changed. Dirty-worktree phase-gate validation fails closed with
`worktree_not_exact_head`, as required.

The first independent post-change verification found that a valid newly defined
`NOT_STARTED` successor was derived correctly but projected as a repair. That
path is fixed with an end-to-end valid-repository regression and explicit failed
entry-condition handling. Rereview then exposed transition acceptance despite a
failed non-transition entry and vacuous start with no entry conditions; both now
fail closed under validated regressions. Final focused rereview and the
implementation revision's exact GitHub/Vercel conclusions must still be recorded
before this repair is considered published. The final focused rereview returned
`ACCEPT` with no material findings after 137 controller tests plus independent
Ruff, strict mypy, hash/state, and diff checks. F04 remains `Revise` after
publication because other bounded defects remain.

## Prior Run 25 handoff (superseded by Run 26)

Run 26 completed this prior alias-reversion handoff. The current next action is
`f04.deployed_page_verification`; do not begin it in this invocation.
