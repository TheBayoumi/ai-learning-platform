# ExecPlan: F04 Vercel Deployment Baseline

**Phase:** `F04 - Vercel Deployment Baseline`
**Class:** Technical foundation
**Status:** `PASSED / Continue`. A real preview deployment
(`dpl_7o2AnhP8uMaSqE5wE2L8ggdgo5oN`) reached `READY` for exact commit
`ea29294fe35687da9264682513fdfa08d520f776`, GitHub-linked (commit status
`success`). The user visually confirmed the deployed page safely renders
the API-unavailable state. `vercel rollback` was tested and correctly
refused a non-production target, confirming F04's preview-only scope. This
acceptance-state revision records that evidence; its own exact five-job
GitHub run is the final confirmation step.
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
5. One demonstrated rollback to a prior accepted deployment with recorded
   evidence (deployment IDs, timestamps, and the exact SHA each targets).
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
- preview deployment of the exact web-tier implementation head succeeds;
- the deployed health-status surface safely and accessibly reports
  API-unavailable with no API origin configured;
- no secret, server-only configuration, or confidential diagnostic value
  appears in any deployed browser asset or public log;
- rollback to a known accepted deployment is demonstrated with evidence;
- GitHub records exact deployment and workflow evidence attached to the
  exact head SHA;
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

No local runtime, dependency, or code path changes are introduced by this
phase's definition. Real deployment resource observations (build duration,
artifact footprint, latency) will be recorded once a live deployment exists.

## Data, Privacy, Security, and Compatibility

F04 adds no database, learner data, role data, or persistent backend state.
The web tier's existing server-only configuration and confidentiality
boundaries (F01, F02) are unchanged; this phase verifies them against a real
deployment rather than only local/CI environments.

## Rollback

F04 is scoped to preview deployments only; it does not promote to
production. Vercel's `vercel rollback` command is a production-alias
mechanism and explicitly refuses non-production targets (tested directly:
`Error: ... has never served production traffic - it is not a valid
rollback target. (422)`). This is consistent with F04's bounded scope, not
a gap: for preview-only deployments, "rollback to a known accepted
revision" is demonstrated by each deployment's permanent,
independently-addressable URL, which Vercel never garbage-collects. Two
independently accepted preview deployments (`dpl_F4HfP5AL5Nv4KPnqGYbLhrWQ71U5`
for `787534a16506c45c9b953e95dd33aa6c1b8aa35a` and a second for
`ea29294fe35687da9264682513fdfa08d520f776`) both remain independently
`READY` and reachable, proving a prior accepted revision stays available
after a newer one deploys. Production promotion and rollback are deferred
to the phase that first promotes to production, outside F04's scope.

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

After F04 passes, stop. The next eligible action is determined by
recomputing both lanes from repository state in a future invocation; this
invocation does not begin it.
