# ExecPlan: F04 Vercel Deployment Baseline

**Phase:** `F04 - Vercel Deployment Baseline`
**Class:** Technical foundation
**Status:** `FAILED_RETRYABLE / Revise`. Starting repair head
`ceaf60d2ce5adf826b8268c32e513569a35eeb0c` passed both exact GitHub workflow
runs and has a GitHub-linked `READY` preview deployment
(`dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z`). The dedicated non-production alias proof
in `plans/F04-vercel-alias-reversion-evidence.json` now resolves only
`f04.rollback_reversion`: the same hostname moved B to prior preview A and back
to intended final preview B, with alias ownership, exact deployment ID, exact
Git SHA, and protected application HTTP evidence after every transition. F04
remains `FAILED_RETRYABLE / Revise` because deployed-page automation,
version-controlled deployment reproducibility, required measurements, and
repository payload hygiene remain incomplete.
**Decision owner:** Primary agent under the autonomous-decision rule
**Integration surface:** A pull request on `automation/f04-vercel-deployment-baseline`
**Validation lane:** `V00` remains `WAITING_EXTERNAL / Revise`; `V01` remains locked.

## Objective

Establish the smallest reproducible Vercel deployment baseline for the
existing role-neutral Next.js web tier, with GitHub-linked revision evidence,
explicit preview/production environment separation, safe server-only
configuration, rollback evidence, and bounded resource/cost observations. A
successful deployment is not production readiness and does not pass V00,
unlock V01, or authorize product functionality.

## Topology decision (required pre-implementation decision)

GitHub issue #3 requires resolving the tension between the repository's
provisional Vercel candidacy and the technical constitution before
implementation, using current Vercel documentation and actual
connected-project evidence rather than assumption.

`specs/tech-stack.md` (Decision Status → Approved, row "Runtime") approves
**"Containers on a managed PaaS"** as the backend runtime. Under that
document's own authority rule ("Approved decisions are binding. Changing one
requires an explicit constitution update."), only the **PaaS vendor** is
listed as Provisional (`### Provisional` → "Cloud and PaaS vendor") — the
container runtime model itself is not open for selection inside a bounded
foundation phase.

Current Vercel documentation (fetched 2026-07-17) confirms Vercel's Python
runtime does support ASGI frameworks including FastAPI via a dedicated
framework preset, but its execution model is fundamentally serverless:
functions are invoked per request, instances are paused between invocations,
and Vercel's own guidance is to keep state in an external store rather than
instance memory. This is a materially different runtime model from
"containers on a managed PaaS," so deploying the FastAPI backend to Vercel
would not satisfy the approved constitutional decision — it would require
amending it, which this bounded phase does not do.

**Decision: Option 2.** Vercel hosts only the Next.js web tier (`apps/web`),
a first-class, unmodified use of the Vercel platform. The FastAPI API's
deployment remains governed by the existing approved
containers-on-managed-PaaS decision; vendor selection is deferred to a later,
separately gated phase. This is the narrower, reversible interpretation and
requires no constitutional amendment.

Sources consulted: `vercel.com/docs/frameworks/backend/fastapi`,
`vercel.com/docs/functions/runtimes/python`, `vercel.com/docs/fluid-compute`.

## Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| F03 passed on both revisions | `plans/F03-github-phase-gate-control-plane.md`; implementation SHA `fe49b609767e27d52fae999c229502ed98866dff` (runs `29528587173`, `29528587169`); acceptance SHA `c2938f2d0496088ea117acf387424530ad0b4c59` (runs `29577006084`, `29577007722`); all ten job executions per revision `success` | Passed |
| GitHub issue #3 is the approved control contract | `https://github.com/TheBayoumi/ai-learning-platform/issues/3` | Passed |
| Topology decision recorded | This ExecPlan; `specs/roadmap.md` F04 section | Passed |
| No Vercel secret or connected project already exists | `gh secret list` returned empty; `gh api repos/.../commits/HEAD/check-runs` shows only the five existing F03 jobs; `gh api repos/.../commits/HEAD/status` shows zero commit statuses; `gh pr list` shows no PR referencing Vercel | Passed (recorded, not assumed) |

## Scope

Deploy only `apps/web` to Vercel. The FastAPI API is not deployed to Vercel
in this phase. The deployed web app's existing F01 health-status surface
must safely report the accessible API-unavailable state with no API origin
configured, proving the already-built unavailable-state behavior in a real
deployed environment rather than only in local/CI tests. No new backend
runtime, container image, or PaaS vendor selection is introduced.

## Outputs

1. Vercel project configuration scoping the project root to `apps/web`
   (`vercel.json` or equivalent), committed with no secret values.
2. Documented preview and production environment separation.
3. A verification step confirming no server-only secret, confidential
   diagnostic value, or raw environment value appears in any deployed
   browser-served asset (extending F02's existing browser-confidentiality
   scan to run against the real deployed build output).
4. Deployment status attached to the exact pull-request head SHA, failing
   closed on a missing, pending, or failed deployment; no previous-head
   deployment is accepted as evidence for a newer head.
5. One demonstrated traffic-moving reversion to a prior accepted deployment
   with recorded evidence (deployment IDs, aliases, timestamps, commands,
   HTTP results, exact SHAs, and the restored final target). A rejected command
   or continued reachability of immutable preview URLs does not qualify.
6. Recorded build duration, artifact footprint, and cold/warm health-surface
   latency observations from the real deployment.

## Non-Goals

- FastAPI or API deployment of any kind.
- PaaS vendor selection for the API.
- PostgreSQL, ORM, migrations, persistence, queues, object storage,
  authentication, tenancy, learner or role data.
- Curriculum, assessment, mastery, readiness, simulations, LLM access.
- Production telemetry backend, beta traffic, SLA, compliance certification,
  or commercial launch.
- V00 evidence or V01 unlock.

## Exit Gate

F04 passes only when:

- the topology decision is recorded (done, above);
- version-controlled, non-secret configuration reproduces the `apps/web`
  project boundary and a compatible pinned Node/npm installation;
- preview deployment of the exact web-tier implementation head succeeds;
- the deployed health-status surface safely and accessibly reports
  API-unavailable with no API origin configured;
- no secret, server-only configuration, or confidential diagnostic value
  appears in any deployed browser asset or public log;
- traffic is demonstrably reverted to a known accepted deployment, exact served
  revisions are verified, and the intended final target is restored with evidence;
- GitHub records exact deployment and workflow evidence attached to the
  exact head SHA;
- build duration, artifact footprint, cache impact, cold/warm page latency,
  runtime versions, and bounded cost observations are recorded;
- the tracked oversized archive is removed from the current tree after its
  references and impact are verified, without history rewriting, and a narrow
  ignore rule prevents recurrence;
- all five F03 checks (API quality, Web quality, Runtime smoke, Phase gate,
  Gate projection) remain green on the exact head;
- independent verification finds no scope leakage, no FastAPI or
  PaaS-vendor decision, and no V00/V01 bypass; and
- a separate acceptance-state revision passes its own required checks and
  deployment evidence.

## Dependencies

`F03` only. F04 neither depends on nor satisfies `V00`, does not unlock
`V01`, does not select a PaaS vendor for the API, and makes no
production-readiness, SLA, or commercial-launch claim.

## External Dependency: Vercel Account, Project, and GitHub Connection (resolved)

This phase required a real Vercel account, project, and GitHub Git
integration. This was resolved externally, not fabricated:

- The user created a Vercel account, installed the CLI, logged in, and
  linked project `web` (`prj_xAgw4qL8P9B1L7HUqVEISFE5QeXN`), scoped to
  `apps/web`. `.vercel/` and `.env.local` are confirmed git-ignored.
- `vercel git connect` initially failed with "You need to add a Login
  Connection to your GitHub account first" (browser OAuth). The user
  authorized this in the Vercel dashboard and reran `vercel git connect`,
  which succeeded.
- Verified via the Vercel REST API (`GET /v9/projects/{id}`): `link.type` is
  `github`, `link.repo` is `ai-learning-platform`, `link.org` is
  `TheBayoumi`, `link.productionBranch` is `main`.
- Found and fixed a real defect: the project's `rootDirectory` was `.` (repo
  root), which would have broken every GitHub-triggered preview build with
  "No Next.js version detected" (reproduced earlier when deploying from the
  repo root). Fixed via `PATCH /v9/projects/{id}` with
  `rootDirectory=apps/web`; confirmed via a follow-up `GET` showing
  `rootDirectory=apps/web`, `framework=nextjs`.

No GitHub Actions secret (`VERCEL_TOKEN`, `VERCEL_ORG_ID`,
`VERCEL_PROJECT_ID`) was created; Vercel's native GitHub App integration
requires none. Preview deployments and their GitHub check/deployment status
are produced automatically by Vercel on push, tied to the exact commit SHA.

## Performance and Resources

The live preview exists, but the required build duration, artifact footprint,
cache impact, cold/warm page latency, runtime-version, and bounded cost
observations have not yet been recorded. These remain exit-gate outputs; the
earlier acceptance did not make the missing measurements optional.

The alias proof used three supported REST assignments and bounded control/data
plane verification. Assignment calls completed in 1,945-2,209 ms, bounded alias
and deployment verification completed in 7,683-24,480 ms with one observed
attempt per transition, and protected page requests completed in 3,638-5,872
ms. The proof added no learner data, model call, persistent runtime, or ongoing
compute cost; the dedicated alias remains on B for auditability.

The alias-reversion repair passed 21 focused evidence tests and all 158
controller tests. Canonical generation, Ruff, strict mypy, and all 426 API tests
passed at 97% total line coverage; clean web install, lint, strict typecheck, 97
tests, production build, browser confidentiality scan, and the 48-event
cross-process runtime smoke also passed. Local Node 25.2.1 differs from `.nvmrc`
24.18.0 and the Vercel project's 24.x setting, so these results do not satisfy
the deployment reproducibility or real-deployment measurement outputs above.

Independent post-change verification initially found and reproduced three
fail-open successor/entry-transition cases. All were repaired with validated
repository regressions; final focused rereview returned `ACCEPT` with no material
findings. This accepts only the controller/state repair. F04 remains `Revise`
until every exit requirement is satisfied.

Run 26 independent read-only verification returned `ACCEPT` for the bounded
alias-reversion repair with no material findings after independently checking
the live final alias, deployment/SHA chain, HTTP behavior, isolation, evidence
schemas, authoritative hashes, controller suite, and complete API gate. This
accepts only `f04.rollback_reversion`; it does not accept F04.

## Data, Privacy, Security, and Compatibility

F04 adds no database, learner data, role data, or persistent backend state.
The web tier's existing server-only configuration and confidentiality
boundaries (F01, F02) are unchanged; this phase verifies them against a real
deployment rather than only local/CI environments.

## Rollback

F04 is scoped to preview deployments only; it does not promote to production.
The attempted `vercel rollback` call returned HTTP 422 because the preview had
never served production traffic. That failure correctly proves the command is
inapplicable to this target; it does not prove rollback. Likewise, two
independently addressable `READY` preview URLs demonstrate historical revision
access, not movement of served traffic from a newer revision back to an older
one.

F04 therefore remains `Revise`. The bounded traffic-reversion repair is now
complete using the dedicated non-production verification alias
`f04-reversion-proof-web.vercel.app` and Vercel's supported
`POST /v2/deployments/{deployment-id}/aliases` endpoint:

1. Initial assignment placed the alias on B
   (`dpl_GdiQHUzEAKrXo1LE4hcoUu1de22Z`,
   `ceaf60d2ce5adf826b8268c32e513569a35eeb0c`).
2. Backward reversion moved the same alias to A
   (`dpl_64G3A2Zim5iWcQ2YzrQnW9runPii`,
   `ca08301b46e49945a805f20a07866a931a8e81e0`); the response identified B as
   `oldDeploymentId`.
3. Final restoration moved the same alias from A back to B; the response
   identified A as `oldDeploymentId`.

After every assignment, bounded polling proved exclusive alias ownership, the
target deployment's expected project, `READY` preview state, and exact Git SHA.
Authenticated `vercel curl` requests returned HTTP 200 application HTML with no
redirect and the accessible API-unavailable state, while loopback origins,
health paths, trace identifiers, and confidential diagnostic markers were
absent. The Git-managed branch alias and production aliases were unchanged, and
the proof alias is intentionally left on B. The sanitized machine-readable
evidence contains no credentials, bypass material, cookies, temporary share
URLs, raw authorization headers, or full HTML. The earlier rejected
`vercel rollback` command remains recorded as rejected-command evidence and is
not relabeled as success.

Separately: to remove F04 entirely, remove the Vercel project connection
and revert the bounded F04 web deployment configuration. F00-F03 remain
fully operational locally and in CI, independent of any Vercel deployment
state.

## Gate Decision Rules

- `Continue`: the topology decision is recorded, a real preview deployment
  succeeds with complete exit-gate evidence, and a separate acceptance-state
  revision passes its own required checks.
- `Revise`: a repairable configuration, secret-exposure, or evidence defect
  is found.
- `Narrow`: even the web-only scope requires a capability outside this
  phase's non-goals.
- `Stop`: acceptance would require FastAPI deployment, PaaS vendor
  selection, committed credentials, fabricated evidence, or a
  validation-gate bypass.

## Next Boundary

F04 has not passed. Stop after publishing and verifying this bounded
verification-alias repair. The only next eligible action is
`f04.deployed_page_verification`. Do not implement that verifier, build
reproducibility, measurements, archive hygiene, F05, merge, or issue closure in
this invocation.
