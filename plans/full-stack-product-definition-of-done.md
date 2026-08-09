# AI Career Learning Platform — Full-Stack Product Definition of Done

## Why this document exists

The G01–G09 program hardens the deterministic learning, evidence, provenance, readiness, persistence, and deployment kernel. It is **not** by itself sufficient to call the commercial learner product complete.

The product is complete only when the approved technical constitution and mission are exposed as coherent, usable, production-grade end-to-end workflows for an adult B2C learner and the required internal human reviewers. Internal Python services, route-shaped pages, static projections, or test-only authority paths do not satisfy this definition.

This document preserves the external V00–V22 validation boundary. Engineering may build these capabilities, but implementation never fabricates practitioner, cohort, assessment-validity, or market evidence.

## Product completion super-goal

A new adult learner must be able to create an account, resolve a career Target, complete an evidence-based diagnosis, receive a dynamic learner-specific curriculum, learn through the policy-controlled tutor, complete unique tasks/projects/work simulations, upload and version real artifacts, receive trusted evaluation, complete no-hint/retention/transfer verification, respond to modification/debugging/defense challenges, inspect disputes and evidence, see exact remaining readiness gaps, change constraints and trigger deterministic replanning, resume on another device, export/delete their data, and recover safely from provider/job/network failures.

A qualified human reviewer must be able to review the role contract, Blueprints/rubrics, contested evidence, work provenance, simulation outcomes, and any externally used readiness report without bypassing append-only evidence history.

## Non-negotiable product rule

**No capability counts as product-complete while it exists only inside domain/service code.** Every learner-facing or reviewer-facing capability required by the mission must have:

1. an ownership-checked API/query or command surface;
2. a typed web client contract;
3. a usable web workflow with loading/empty/error/retry states;
4. durable persistence and replay semantics where evidence-bearing;
5. authorization and privacy controls;
6. integration, failure, concurrency, and end-to-end tests; and
7. production verification on the exact deployed main revision.

## P01 — Identity, account, and session ownership

- Implement the approved managed-OIDC boundary with provider-neutral account/subject mappings.
- Support sign-up, sign-in, sign-out, session refresh, account recovery boundary, and authenticated ownership checks.
- Preserve a safe migration path from existing anonymous durable accounts to an authenticated account without duplicating or losing learner evidence.
- A learner can resume the same durable account and active plan on another browser/device.
- API authorization must not trust browser-supplied account identifiers.
- Internal reviewer/admin roles are explicit and auditable; organization tenancy remains deferred.
- Export/delete operate on the authenticated account and cover all owned learner data/artifacts subject to approved retention rules.

## P02 — Persisted RoleProfile, CompetencyGraph, Overlay, Blueprint, and review administration

- Replace runtime-only catalog authority with PostgreSQL-backed, versioned repository interfaces for RoleProfile, CompetencyGraph nodes/edges, overlays, evidence requirements, provenance, effective dates, expiry, and review state.
- Persist ItemFamily, Blueprint, rubric, verifier, assistance policy, trust state, approval decisions, and version history.
- Provide internal author/reviewer UI for draft → review → publish/trust transitions with append-only decisions.
- Learner planning binds to exact published versions; a later publication never silently rewrites prior learner evidence.
- Target/RoleProfile changes create explicit remap/replan deltas.

## P03 — Diagnostic and trusted assessment product loop

- Onboarding does not stop at self-rating. It launches an adaptive diagnostic that selects trusted learner-bound ItemInstances against uncertainty and prerequisite gaps.
- Public learner APIs support diagnostic start/resume/submit and show why a check is requested without leaking protected answers.
- Assessment/evaluator execution happens through idempotent background jobs and trusted server-side verdict routes, not hidden test helpers.
- Item validation/trust, exposure, leakage, difficulty, reasoning, assistance, and evaluator confidence are visible to the appropriate learner/reviewer surfaces.
- Invalid/low-confidence/conflicting/disputed output fails closed and opens a visible review or stronger-evidence path.

## P04 — Complete adaptive learning runtime

- The learner dashboard is a real scheduler over current plan, reviews, probes, projects, and blocked evidence—not a static PlanView renderer.
- Learning sessions combine instruction, Socratic tutoring, practice, retrieval, explain-back, reflection, and verification while recording assistance/hint use.
- The policy engine chooses the next pedagogical action; the learner cannot manually force evidence authority.
- Accepted evidence, misconceptions, failed work, forgetting, capacity changes, Target changes, and due probes trigger deterministic replanning and a readable plan delta.
- Scheduled immediate/7-day/30-day/transfer obligations appear in a learner calendar/queue and survive logout/device changes.
- Provider outage degrades coaching safely while deterministic work, review scheduling, and evidence integrity remain usable.

## P05 — Real project, artifact, and work-simulation workspace

- Add S3-compatible object storage behind a provider-neutral artifact interface.
- Learners can create/upload artifact versions, repositories/files or structured submissions, checkpoints, source attribution, assistance disclosure, and modification/debugging notes.
- Every artifact is bound to the exact learner, Instance, Blueprint, plan version, content hash, and evidence candidate.
- Serve unique learner-bound Task/Project/WorkSimulation Instances through product APIs and UI; exact/near-duplicate cohort collision checks remain fail closed.
- Provide hidden modification/debugging challenges and defense/explain-back workflows.
- Where executable work is required, use an isolated ephemeral resource-limited runner outside API/evidence workers with network/secret/time/artifact controls.
- A polished upload alone can never advance mastery/readiness.

## P06 — Evidence, disputes, human review, and readiness product surfaces

- Learners can inspect the complete evidence ledger, evaluation history, provenance status, assistance conditions, retention/transfer status, disputes, stale evidence, misconceptions, and exact blockers.
- Learners can dispute an eligible verdict without mutating prior history.
- Internal reviewers have an ownership/permission-checked queue for contested evidence, Blueprint/rubric review, simulation review, and readiness-report approval.
- Reviewer decisions append structured evidence and never silently overwrite historical verdicts.
- Readiness UI is computed against one exact RoleProfile version and exposes mandatory gaps, evidence quality, realistic-work status, uncertainty, exclusions, overlays, and freshness.
- `ready_against_profile` and externally used reports remain impossible until external validation and required human approval are recorded.

## P07 — Background processing, LLM routing, observability, retention, and operational control

- Implement PostgreSQL-backed jobs for evaluation, Item/Instance validation, retention probes, projection rebuild, replay, artifact processing, reports, and outbox delivery.
- Jobs are idempotent, retryable, observable, dead-lettered visibly, and cannot duplicate evidence.
- All model calls use a provider-neutral versioned gateway with recorded route/model/prompt/schema/settings/latency/token metadata and at least one contract-tested alternate adapter before beta.
- Implement bounded raw transcript storage separated from structured evidence, with default 30-day deletion policy pending legal review.
- OpenTelemetry/structured metrics cover request → tutoring → evaluation → transition → job correlation.
- Measure p50/p95 first-token and end-to-end latency, model/token cost per session, cost per verified competency, schema failure, evaluator disagreement, provider fallback, job retry/dead-letter, projection lag, replay failure, and tutor-move failure.
- Browser bundles/log surfaces contain no secrets, raw sensitive payloads, or confidential diagnostics.

## P08 — Commercial-quality learner web product and exact-production acceptance

The web product must provide coherent production-grade flows for:

- marketing/landing and truthful claim boundary;
- sign-up/sign-in/account recovery boundary;
- Target onboarding;
- adaptive diagnostic;
- dashboard/today queue;
- learning session + tutor;
- assessments and scheduled probes;
- roadmap/plan deltas;
- projects/work simulations;
- artifact upload/version/checkpoints;
- provenance/challenges/defense;
- evidence/disputes;
- readiness/gaps;
- profile, constraints, target changes, data export, and deletion;
- reviewer/admin queues required by the initial B2C evidence model.

Every surface must have responsive layout, keyboard/accessibility support, loading, empty, offline/network, stale/conflict, permission, provider-failure, and retry states. No page may present an internal capability as complete while the command path is unavailable.

## Full-stack acceptance journey

From a clean production account on the exact deployed main SHA, an automated + human-reviewed canary must prove:

1. sign in and account ownership;
2. resolve Target and create durable learner state;
3. complete diagnostic and receive a learner-specific plan;
4. run a tutor turn and record assistance policy;
5. complete a generated learner-bound activity;
6. upload/version an artifact and record checkpoints/provenance;
7. receive trusted evaluation through the job/evaluator path;
8. complete at least one independent probe and exercise scheduling for delayed retention/transfer;
9. complete a modification/debugging or defense challenge;
10. observe deterministic replan/readiness blockers from the resulting evidence;
11. dispute/review a test verdict through the human-review boundary;
12. resume the same account/plan from a fresh session;
13. export account data and verify replay;
14. delete the account and prove protected data/artifact access is revoked while allowed unlinkable collision tombstones remain; and
15. verify production telemetry/operational evidence contains no secret or sensitive payload leakage.

The canary may use synthetic test identities/data, but it must exercise the same production routes, persistence, jobs, authorization, object storage, and model/evaluator boundaries as real learners.

## What is explicitly outside initial product completion

Do not expand into employer dashboards, organization tenancy, schools/minors, marketplace/social features, public credentials, native mobile, Kubernetes, microservices, or guaranteed job placement. Those remain deferred/non-goals unless separately approved.

## Program sequence

- G01–G08: preserve as completed learning-kernel work when their evidence remains valid.
- G09: integration hardening is **not terminal**; it becomes the bridge into this full-stack program and must not mark the repository product-complete by itself.
- P01 → P08: execute sequentially from the exact production-verified main of the preceding phase, unless an explicitly independent infrastructure task can be proven not to stack unverified behavior.

## Terminal definition

The repository may state **FULL_STACK_PRODUCT_COMPLETE** only when P01–P08 are all exact-head green, review-clean, merged, exact-main production-verified, the full-stack acceptance journey passes, no temporary automation or diagnostic artifacts remain, and branch hygiene leaves only `main` plus any intentionally active validation branch.

External validation status remains separate and truthful even after engineering completion.