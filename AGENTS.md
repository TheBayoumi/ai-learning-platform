# AI Career Learning Platform — Agent Operating Contract

## Purpose

This repository builds a persistent one-to-one AI tutoring, mastery, and role-readiness engine for adult career acceleration.

The product is not a chatbot, static course library, quiz application, school, credential marketplace, or hiring guarantee.

## Authoritative Sources

Read these before proposing or making material changes:

1. `docs/strategy/ai-learning-platform-strategy.md`
2. `specs/mission.md`
3. `specs/tech-stack.md`
4. `specs/roadmap.md`
5. The current repository and its executable tests

Precedence:

1. The user's explicit instruction for the current task
2. Approved specifications
3. Strategy
4. Verified repository behavior
5. Clearly labeled provisional assumptions

Do not silently resolve contradictions. Report the conflict and use the narrowest reversible interpretation that permits safe progress.

## Product Invariants

Every change must preserve these invariants unless the user explicitly changes the constitution:

- The first commercial product serves adults aged 18+ pursuing career entry or transition.
- The initial role is provisional and must pass role-selection gates before content production.
- A target resolves role, seniority, labor market, timeline, and applicable overlays.
- A `RoleProfile` defines required outcomes; it is not a fixed syllabus.
- Curricula are versioned, learner-specific, and recomputed from evidence and constraints.
- Learners targeting the same role must not receive identical served tasks, projects, or work simulations.
- Shared blueprints and rubrics preserve comparability; each served instance is unique and traceable.
- LLMs may converse, generate, evaluate, and propose. They do not own mastery, curriculum, evidence acceptance, or readiness state.
- Mastery, planning, evidence, and readiness transitions are deterministic, versioned, auditable, and replayable.
- Completion is not mastery.
- Mastery requires independent no-hint performance, reasoning evidence, delayed retention, and transfer where applicable.
- Readiness claims require realistic work evidence, artifact provenance, and the learner's ability to explain, modify, debug, and defend the work.
- Readiness is reported only against a named, versioned role contract and with stated uncertainty.
- The product must not guarantee employment, promotion, compensation, or acceptance by every employer.
- External first-year readiness reports require human approval.
- School, minor-facing, enterprise-tenancy, marketplace, credentialing, and multi-role expansion are outside the initial validation path unless separately approved.

## Repository Workflow

### 1. Inspect before editing

Before changing files:

- Read the relevant strategy and specification sections.
- Inspect repository structure, manifests, tests, migrations, configuration, and nearby code.
- Identify the current roadmap phase and its entry conditions.
- State material assumptions in the working notes or execution plan.
- Reuse existing abstractions when they satisfy the constitution; do not create parallel systems.

### 2. Use subagents for bounded independent work

Delegate when the task has at least two independent analysis streams, affects multiple constitutional domains, spans frontend/backend/data/evaluation boundaries, or requires substantial repository exploration.

Use parallel read-only subagents for:

- strategy and mission drift review;
- learning-evidence and assessment-validity review;
- architecture and deterministic-state review;
- roadmap and phase-gate review;
- test, replay, privacy, security, or performance review.

Subagent rules:

- Give each agent one narrow question, concrete files to inspect, and a required output format.
- Require file paths, symbols, evidence, risks, and a recommended disposition.
- Keep review agents read-only.
- Use at most one write-capable worker for a shared working tree at a time.
- The parent agent owns synthesis and final decisions.
- Continue independent parent work while subagents run.
- Before finalizing, collect every completed result and reconcile disagreements.
- Do not repeatedly emit empty “waiting for agents” cycles. After one status check, continue useful work.
- If an agent fails, is unavailable, or times out, record that fact and perform the missing review in the parent thread.
- Do not treat agent agreement as evidence by itself; verify findings against files and tests.

### 3. Recommended delegation matrix

For constitution, strategy, or cross-cutting design work, spawn in parallel:

- `mission_guardian`
- `learning_evidence_reviewer`
- `architecture_guardian`
- `roadmap_gate_reviewer`

Then use `verification_reviewer` after the parent prepares the integrated change.

For implementation work:

1. Use the built-in `explorer` or a relevant read-only custom reviewer to map the code path.
2. Let the parent write the execution plan and define acceptance criteria.
3. Spawn only one `phase_worker` for the bounded implementation, or let the parent implement.
4. Run `verification_reviewer` independently after implementation.
5. The parent reconciles findings, fixes confirmed issues, and runs final validation.

Do not spawn multiple write-capable agents against the same files.

### 4. Phase discipline

Implement only the smallest roadmap phase or explicitly approved slice.

Every phase must define:

- objective;
- entry conditions;
- files or components in scope;
- non-goals;
- acceptance criteria;
- tests and evidence;
- performance and cost observations where relevant;
- continue, revise, narrow, or stop decision.

Do not start the next phase merely because code was written. The current phase's evidence gate must pass.

For work expected to span multiple sessions or substantial milestones, create or update an ExecPlan under `plans/`. The plan must be self-contained and remain current as implementation progresses.

### 5. Ask only for unresolved decisions

Do not ask questions already answered by the strategy, specifications, repository, or current conversation.

When a material product decision is unresolved and blocks safe work:

- group related questions;
- provide a recommended default and its trade-off;
- distinguish approved, provisional, and deferred choices;
- do not write the blocked decision as though it were approved.

When no genuine blocker exists, use the safest reversible default and label it.

## Architecture Guardrails

- Keep the backend a Python/FastAPI modular monolith during validation unless the constitution changes.
- Keep the web application in Next.js/React with TypeScript.
- PostgreSQL is the transactional system of record.
- Use append-only domain events for evidence-bearing operations and replayable projections for derived learner state.
- Do not event-source configuration or ordinary CRUD merely for uniformity.
- Use an outbox for reliable asynchronous work.
- Keep the initial competency graph in PostgreSQL behind repository interfaces.
- Store learner artifacts and immutable evidence attachments in S3-compatible object storage.
- Start with PostgreSQL-backed jobs; introduce additional brokers only from measured need.
- Keep LLM access behind a provider-neutral, versioned gateway.
- Validate all model outputs against explicit schemas and treat them as untrusted inputs.
- Invalid, disputed, conflicting, or low-confidence evaluator output must not mutate deterministic learner state.
- Version prompts, models, rubrics, policies, blueprints, items, evaluators, and state-transition algorithms.
- Every accepted evidence transition must record provenance sufficient for replay and audit.
- Avoid microservices, Kubernetes, graph databases, dedicated vector databases, and model training during the initial validation unless an approved gate justifies them.

## Implementation Standards

### Python

- Use supported Python versions declared by the repository.
- Apply complete type annotations to production code.
- Use Pydantic models at external and domain boundaries where appropriate.
- Keep domain rules independent from FastAPI handlers, LLM clients, storage adapters, and job runners.
- Handle failures explicitly; do not silently coerce invalid evidence.
- Use structured logging without raw sensitive learner content.

### TypeScript

- Use strict TypeScript.
- Keep server state, client state, and domain state boundaries explicit.
- Validate external payloads at runtime.
- Do not duplicate backend domain rules in the browser.
- Preserve accessibility and keyboard navigation in learner-facing flows.

### Data and migrations

- Migrations must be forward-safe and tested.
- Destructive migrations require an explicit data-preservation or rollback plan.
- Event payloads and public schemas require compatibility handling.
- Projection rebuilds must be deterministic and observable.
- Production data must not be copied into development.

### Testing

Minimum expectations unless the specifications set a stricter requirement:

- At least 95% line coverage for deterministic mastery, curriculum, assessment-state, evidence, and readiness services.
- At least 90% backend line coverage overall.
- Branch coverage for critical rules.
- Mutation testing for high-risk deterministic policies.
- Property-based tests for replay, idempotency, ordering, and invariant preservation.
- Contract tests for LLM providers, authentication, object storage, and background jobs.
- Golden evaluator and transcript regression tests.
- Fault-injection and load tests before beta gates.
- Fixed seeds, pinned dependencies, immutable evaluation datasets, and recorded model identifiers.

Coverage is not sufficient by itself. Tests must prove behavior, failure handling, replayability, isolation, and evidence integrity.

## Required Validation

Before declaring a task complete:

1. Run the narrowest relevant tests during development.
2. Run all affected unit, integration, contract, replay, and migration tests.
3. Run formatting, linting, static typing, and schema checks defined by the repository.
4. Check for product-invariant violations.
5. Check data isolation, privacy, provenance, and deletion implications.
6. Measure latency, memory, throughput, and model cost when the change affects them.
7. Review the diff for unrelated edits and generated artifacts.
8. Ask `verification_reviewer` for an independent read-only review on material changes.
9. Fix confirmed findings, rerun validation, and report remaining uncertainty.

Never report a passing result that was not actually run.

## Reporting Contract

The final response must state:

- what changed;
- why it satisfies the current roadmap phase;
- files changed;
- tests and checks actually run, with results;
- performance and resource implications;
- data migration or compatibility implications;
- unresolved risks or provisional decisions;
- the phase gate disposition: Continue, Revise, Narrow, or Stop.

Do not claim complete-role readiness from proof-slice results.
Do not begin the next roadmap phase unless requested or already included in the approved task.
