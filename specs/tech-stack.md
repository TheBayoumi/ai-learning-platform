# Technical Constitution

## Purpose and Authority

This document defines the technical foundation for the AI Career Learning Platform. Terms have the meanings established in `mission.md`.

- **Approved** decisions are binding. Changing one requires an explicit constitution update.
- **Provisional** decisions may be selected during implementation only within the approved contracts and migration boundaries.
- **Deferred** capabilities are outside the initial validation. They require evidence of need and an explicit scope decision before implementation.
- All numbered architectural contracts below are **Approved** unless marked otherwise.

## Decision Status

### Approved

Technologies are approved because they satisfy a stated requirement, not because they are popular.

| Boundary | Decision | Requirement served | Constraint and operational cost | Migration boundary |
|---|---|---|---|---|
| Repository | Monorepo | Version web, API contracts, domain schemas, tests, and infrastructure together for a small team | Coordinated CI and release discipline | Split only after measured ownership or deployment-isolation needs justify it |
| Web | Next.js, React, and TypeScript | Web-first typed learner experience and streamed tutoring | JavaScript toolchain and framework upgrade cost | Domain logic remains behind OpenAPI; deployment mode remains replaceable |
| Backend | Python and FastAPI modular monolith | One backend runtime for learning, evaluation, assessment, analytics, and future ML work | Module boundaries must be enforced inside one deployable | Extract a service only after measured scaling, reliability, or ownership pressure |
| API | REST/OpenAPI and Server-Sent Events | Explicit request-response contracts and low-latency tutor streaming | Schema-versioning work; SSE is not a general bidirectional protocol | Add another transport only without changing domain ownership or evidence contracts |
| Transactional data | PostgreSQL | Transactional record, bounded relational graph, events, projections, and jobs with low initial operations | Replay, indexing, recursive-query, and contention costs | Repository and event interfaces permit specialized stores when measurements justify them |
| Evidence history | Append-only domain events, transactional outbox, replayable projections | Reconstruct mastery, curriculum, evidence, and readiness | Event-schema governance, idempotency, and replay-test cost | Delivery infrastructure may change, but event contracts and the system-of-record boundary remain |
| Graph storage | Relational nodes and edges in PostgreSQL | A 40-80-node proof slice does not justify another database | Complex traversals may become harder to author or tune | Graph repositories isolate storage; reconsider only from measured query or authoring limits |
| Artifacts | S3-compatible object storage | Store large learner artifacts, simulations, reports, and immutable evidence attachments | Lifecycle, access-control, and consistency operations | Domain records use an object-storage interface, not vendor-specific URLs |
| Background work | PostgreSQL-backed jobs initially | Reliable asynchronous work with minimal infrastructure | Database contention and limited long-running orchestration | Replace through a job interface only after measured limits |
| Identity | Managed OIDC | Avoid owning authentication security while supporting adult individual accounts | Vendor cost and availability dependency | Domain accounts retain provider-neutral subject mappings and authorization rules |
| LLM access | Provider-neutral, versioned gateway | Select providers by measured quality, latency, cost, privacy, and availability without surrendering state ownership | Adapter, evaluation, and fallback maintenance | At least one alternate adapter is contract-tested before beta |
| Telemetry | OpenTelemetry plus structured logs, metrics, traces, and audit records | End-to-end correlation without fixing a telemetry vendor | Instrumentation and telemetry-storage cost | Exporters and backends remain replaceable |
| Runtime | Containers on a managed PaaS | Reproducible deployment with operational load suitable for 2-4 engineers | PaaS limits, vendor cost, and possible later migration | Portable images, external configuration, and version-controlled infrastructure define the boundary |

### Provisional

The following choices are not approved technologies or parameters yet:

- Exact Next.js deployment mode.
- ORM and migration tooling.
- PostgreSQL-backed job implementation.
- Managed OIDC vendor.
- Cloud and PaaS vendor.
- Object-storage vendor.
- Telemetry backend.
- Primary and fallback LLM providers and exact models.
- Final raw-transcript retention duration after legal review; the approved default is 30 days.
- Initial mastery-model parameters.
- Psychometric model beyond the proof-stage deterministic implementation.
- Exact isolated execution mechanism for learner-controlled code and simulations.

A Provisional choice must preserve the approved interfaces, audit requirements, replay behavior, privacy rules, and testing gates. Selection evidence must record requirement fit, operational cost, failure behavior, and replacement path.

### Deferred

- Microservices.
- Kubernetes.
- Graph database.
- Dedicated vector database.
- Multi-region active-active deployment.
- Enterprise tenancy.
- Employer dashboards.
- School or minor-facing identity and consent.
- Model fine-tuning or model training.
- Native mobile applications.
- Public credentials or automated external readiness certification.

Deferred does not mean pre-approved later. Activation requires evidence from a preceding product phase and a new decision.

## 1. Architecture Principles

1. Structured evidence is authoritative; chat history, model memory, and narrative summaries are not.
2. Deterministic, versioned services own mastery, misconception, assessment, curriculum, evidence acceptance, and readiness state.
3. The `RoleProfile` is an outcome contract, never a syllabus. `CurriculumPlanner` compiles an immutable learner-specific `LearnerPlanVersion`.
4. Shared Blueprints and rubrics define comparable standards; every served task, project, and work simulation is a validated, unique learner-bound Instance.
5. Evidence-bearing history is append-only and replayable. Mutable projections are disposable views, not the only record.
6. Evidence integrity fails closed. Provider or evaluator failure may reduce tutoring capability but must not create or advance mastery or readiness.
7. Domain boundaries remain explicit inside the modular monolith. Infrastructure is accessed through replaceable interfaces.
8. Data collection is minimized, purpose-bound, redacted, and separated by sensitivity.
9. Every consequential decision explains which evidence and versions produced it.
10. The provisional target-role stack is data, not platform coupling. Replacing the first Target must not require replacing the learning engine.

## 2. Web Application Stack

The web application uses Next.js, React, and TypeScript. It owns learner interaction, streamed tutor turns, plan and evidence explanations, disputes, artifact workflows, and human-review surfaces. It does not compute authoritative mastery, planning, evidence acceptance, or readiness decisions.

The exact Next.js rendering and deployment mode is **Provisional**. Browser state and cached UI projections are never authoritative. Reconnection or retry behavior must not duplicate evidence-bearing commands.

## 3. Backend and API Stack

The backend is a Python/FastAPI modular monolith with explicit modules for identity and access, role contracts, assessment, learner state, curriculum planning, tutoring orchestration, task and simulation Instances, evidence, readiness, and audit.

REST/OpenAPI is the command and query contract. Server-Sent Events stream tutoring output. Schemas are versioned and validated at boundaries; generated clients or equivalent contract checks prevent parallel handwritten frontend schemas. No module may bypass another module's ownership by writing its tables directly.

NestJS and a second core backend runtime are rejected for validation because they would duplicate schemas, deployments, observability, and testing without adding validation-stage evidence value. CPU-heavy or untrusted execution must leave the request process through approved job and isolation boundaries, not through a second domain backend.

## 4. Data Storage and Event-History Strategy

PostgreSQL is the transactional system of record. Append-only domain events cover at least:

- learner attempts and attempt steps;
- evaluator verdicts, confidence, conflicts, and disputes;
- hint usage and assistance policy;
- assessment outcomes;
- mastery and misconception transitions;
- `LearnerPlanVersion` creation;
- `RoleProfile` version publication;
- `ReadinessEvidence` and readiness transitions; and
- reviewer decisions.

Each deterministic transition records its input evidence and applicable policy, model, prompt, rubric, `ItemFamily`, `ItemInstance`, Blueprint, Instance, verifier, schema, and algorithm versions. Corrections use new events or recorded reviewer decisions; prior evidence is not silently edited.

The outbox is written in the same transaction as the originating state change. Consumers are idempotent. Mastery, curriculum, evidence, and readiness projections must be rebuildable. Conventional transactional tables remain appropriate for authentication mappings, configuration, content administration, and state that does not require full historical reconstruction. Event-sourcing every entity is rejected.

Directly identifying data must be separated from append-only payloads where deletion would otherwise become impossible. A deletion operation may remove or irreversibly de-identify learner-linked records under the approved retention policy, and replay must never rehydrate deleted personal data.

## 5. Background Jobs and Event Processing

PostgreSQL-backed jobs initially process outbox delivery, projection updates, evaluation, validation, retention probes, replay, artifact processing, and report generation.

Every evidence-affecting job is idempotent and carries correlation, causation, learner, `RoleProfile`, `LearnerPlanVersion`, and applicable version identifiers. Retries cannot duplicate accepted evidence. Failed jobs enter a visible failure or dead-letter state; they do not disappear or silently advance learner state.

Redis, a dedicated broker, or a workflow engine is not introduced until measured queue latency, throughput, retry behavior, or orchestration complexity exceeds defined limits. The job interface, evidence contracts, and idempotency keys survive any migration.

## 6. Authentication and Authorization

Authentication uses managed OIDC. The initial model supports adult individual accounts in one B2C product. Organization accounts and delegated administration are Deferred.

Authorization enforces explicit ownership and permission checks at API, object-storage, reviewer, administrative, and job boundaries. Internal reviewer or administrator roles do not create organization tenancy. Domain records use provider-neutral account identifiers. Artifact and transcript access is purpose-scoped and auditable. A single-product launch is not permission to encode permanently single-tenant assumptions.

## 7. LLM Abstraction and Model Routing

All model calls pass through a provider-neutral, versioned gateway. One primary provider is selected by evaluation; at least one alternate adapter is contract-tested before beta. Exact providers, models, and routes are **Provisional**.

Routing policy is versioned and selects by task type, measured quality, latency, cost, privacy, and availability. Every call records provider, model identifier, route-policy version, prompt version, settings, schema version, latency, token use, and correlation identifiers.

Model output is schema-constrained and untrusted. An LLM may converse, explain, generate, evaluate, and propose actions. It may not directly mutate mastery, misconceptions, curriculum, role requirements, accepted evidence, or readiness. Invalid, low-confidence, conflicting, or disputed verdicts are excluded from deterministic updates and routed to stronger evidence or human review.

Provider failure degrades tutoring before it compromises evidence integrity. A fallback may not silently change evaluator or assistance policy; it creates a versioned route decision and must pass the same evidence gates.

## 8. Deterministic Learning and Readiness Services

Mastery, misconception, forgetting, review scheduling, assessment state, curriculum planning, evidence acceptance, and readiness are owned by deterministic decision cores with explicit inputs and policy versions.

The same accepted evidence and versions produce the same transition. No mandatory competency gap may be offset by content completion, engagement, a polished artifact, or an LLM opinion. During the proof slice, outputs are labeled `partial_profile_evidence`; complete role-readiness statuses are unavailable until the complete role contract and readiness-calibration gates exist.

State services expose pure decision logic separately from persistence and transport so that replay, property tests, mutation tests, and later model changes do not alter ownership.

## 9. Role and Competency Graph Representation

A `RoleProfile` resolves the named role contract: role, seniority, labor market, common baseline, explicit Overlays, exclusions, evidence requirements, provenance, and review validity. A Target binds that contract to the learner timeline and declared constraints. The `RoleProfile` references a versioned `CompetencyGraph`.

The graph uses PostgreSQL relational nodes and typed edges, including prerequisite, component, and transfer relationships. Each role requirement records provenance, confidence, market scope, effective date, reviewer status, and expiry. Industry, company, geography, and stack deltas remain explicit Overlays and cannot silently redefine the common baseline.

Graph access uses repository interfaces. A graph database is not introduced without measured query or authoring evidence that exceeds the operational cost.

## 10. Curriculum-Planning Boundary

`CurriculumPlanner` accepts only versioned `RoleProfile`, `CompetencyGraph`, learner state, structured evidence, declared constraints, active Overlays, `CurriculumPolicyVersion`, and a stable pseudonymous learner-bound plan seed. It emits an immutable `LearnerPlanVersion` and a readable delta from its parent version. The seed selects only among policy-equivalent routes; it may not change requirements, evidence thresholds, prerequisites, or difficulty.

Replanning occurs only from recorded evidence, declared constraint or Target changes, or a new version of the `RoleProfile`, `CompetencyGraph`, Overlay, or `CurriculumPolicyVersion`. The same inputs, versions, and tie-breaking rules reproduce the same plan. An LLM may propose candidate explanations or activities but cannot add or remove required competencies, change thresholds, mark gaps optional, or mutate the active plan.

## 11. Task, Project, and Simulation Blueprint and Instance Model

`TaskBlueprint`, `ProjectBlueprint`, and `WorkSimulationBlueprint` define competency coverage, parameter schema, difficulty envelope, rubric, verifier, assistance policy, and validity window.

Every served Instance is learner-bound and records its Blueprint version, `RoleProfile`, `LearnerPlanVersion`, seed, parameters, context, difficulty target, assistance policy, similarity fingerprint, and validation result. It must be distinct from all retained served-Instance fingerprints across the learner's history and every current or prior cohort while preserving rubric equivalence.

Instance validation checks schema, constraints, rubric coverage, safety, leakage, and solver or executable tests where applicable. A trusted Blueprint does not make an invalid Instance acceptable. Personalization may vary context and constraints but may not change the measured competency, weaken the rubric, or move difficulty outside the approved envelope.

## 12. Evidence and Artifact Provenance

PostgreSQL stores evidence metadata. S3-compatible storage holds artifact bodies and immutable evidence attachments while retained. Every artifact version records a content hash, source Instance, checkpoints, assistance disclosure, modification requests, defense evidence, timestamps, and reviewer or verifier decisions.

Every `ReadinessEvidence` record points to the exact artifact, assessment, project, simulation, or reviewer evidence version used. Disputes and superseding decisions remain visible. Reports disclose evidence freshness, assistance conditions, mandatory gaps, active Overlays, and uncertainty.

A readiness report cannot be used externally during the first year until a human approval decision has been recorded.

## 13. Evaluation and Assessment Infrastructure

Practice and assessment items are learner-bound `ItemInstance`s produced from a versioned `ItemFamily`. The family defines competency coverage, parameter schema, difficulty envelope, answer or solver, exposure controls, and leakage rules; every `ItemInstance` still requires validation. Each `ItemInstance` records its learner binding, seed, parameters, family version, similarity fingerprint, exposure, and validation result and is collision-checked against all retained item history.

Assessment items use this canonical trust pipeline:

`generated_untrusted` -> `verified_practice_item` -> `beta_item` -> `calibrated_item` -> `assessment_item`

Generated-untrusted items are not served. Mechanically verified items are practice-only. Only protected, validated `ItemInstance`s from `ItemFamily` records at `assessment_item` trust may support no-hint, delayed-retention, or transfer evidence. Exposure, difficulty, discrimination, hint use, flags, leakage, and drift support promotion and demotion.

Work-simulation Blueprints use a separate trust path: `authored` -> `expert_reviewed` -> `piloted` -> `calibrated` -> `readiness_grade`. Pilot or calibrated simulation Instances may produce explicitly scoped validation evidence; only `readiness_grade` simulation Instances may support complete-role readiness.

Evaluator step-grading cannot affect mastery before reaching at least 90% agreement on the controlled test set. Failures are categorized, not hidden in an aggregate score. Disputed verdicts remain excluded. Assessment supports no-hint performance, reasoning evidence, immediate, 7-day, and 30-day retention, transfer, artifact defense, modification requests, and unseen work simulations under declared assistance policies.

Learner-controlled code or artifacts may not execute inside the API or evidence-processing workers. Any executable assessment or simulation uses an isolated, ephemeral, resource-limited runner with network, secret, time, and artifact controls. The exact runner is Provisional and must pass security, determinism, and evidence-correlation tests before beta.

The practitioner-readiness agreement metric and threshold are not defined here. Infrastructure must support blinded review, preregistered sampling, minimum sample size, uncertainty, disagreement handling, and separate calibration from evaluator step-grading.

## 14. Observability, Analytics, and Audit History

OpenTelemetry provides cross-boundary instrumentation. Structured logs, metrics, traces, product events, and audit records correlate user request, tutoring session, attempt, evaluator call, deterministic transition, `LearnerPlanVersion`, and background job.

Required operational metrics include:

- p50 and p95 first-token latency;
- end-to-end turn latency;
- model and token cost per session;
- cost per verified competency;
- schema-validation failure rate;
- evaluator disagreement rate;
- provider fallback rate;
- job retry and dead-letter rate;
- projection lag;
- replay failures; and
- tutor-move failure rate.

Product analytics is privacy-safe. Telemetry is diagnostic, not authoritative learning evidence. Telemetry vendor selection is **Provisional**.

## 15. Privacy, Retention, Deletion, and Sensitive Data

The initial product is adults-only. Raw transcripts default to deletion after 30 days; legal review may approve a different duration before beta. Required structured evidence is distilled before deletion, but usefulness does not justify indefinite transcript retention.

Raw conversation data is separated from structured mastery and readiness evidence. Logs, traces, analytics, and model requests are redacted at ingestion. Sensitive inferred attributes are not persisted. Production designs keep directly identifying data out of append-only event payloads wherever deletion would otherwise become impossible. Non-identifying Instance and `ItemInstance` fingerprints must be retained across cohorts for as long as the product claims history-wide uniqueness; they may not contain learner content or directly identifying data. Privacy review may require an irreversible aggregate representation, but it may not remove the collision-prevention function while that claim remains active.

Account export and deletion cover domain data and stored artifacts. Deletion behavior, permitted residual audit records, retention periods, and data residency must be approved by legal and privacy review before closed beta. The company must not claim compliance with a named regime until final vendors, contracts, markets, and data flows have been reviewed.

## 16. Testing Strategy

Minimum gates are:

- At least 95% line coverage for deterministic mastery, curriculum-planning, assessment-state, evidence, and readiness services.
- At least 90% backend line coverage overall.
- Branch coverage and mutation testing for critical deterministic rules.
- Property-based tests for replay, idempotency, monotonic evidence rules, and plan reproducibility.
- Contract tests for LLM adapters, OIDC, object storage, and background jobs.
- Golden tutoring-transcript and evaluator-agreement regression suites.
- Replay tests proving identical results from identical evidence and version inputs.
- Integration tests for outbox delivery, projection rebuild, retries, disputes, authorization, export, deletion, and redaction.
- End-to-end tests for critical learner and reviewer workflows.
- Load and fault-injection tests before beta.

Coverage alone is not acceptance. A suite that does not exercise evidence integrity, independent performance, failure paths, and replay cannot pass the beta gate.

## 17. Reproducibility and Versioning Requirements

Recorded versions include the `RoleProfile`, `CompetencyGraph`, `CurriculumPolicyVersion`, `LearnerPlanVersion`, mastery policy, readiness policy, algorithm, model, route, prompt, schema, rubric, `ItemFamily`, `ItemInstance`, Blueprint, Instance, verifier, assistance policy, dependency set, and Instance seed.

Dependencies are pinned. Evaluation datasets are immutable and versioned. Generated Instances record seeds and parameters. A deterministic replay uses the recorded structured verdict and accepted evidence rather than making a fresh nondeterministic model call. Re-evaluating with a new model or prompt creates new evidence and a new projection version; it does not rewrite prior history.

Schema and policy migrations preserve prior interpretation or supply an explicit, tested migration and replay path.

## 18. Performance Budgets and Resource Constraints

The validation gate is p95 first-token latency below 2.5 seconds. The mature target is below 2 seconds for normal turn-level moves. Both are measured in representative conditions and reported with end-to-end latency and failure rates.

Session, learner, and verified-competency cost ceilings must be derived from measured prototypes and approved before closed beta. Queue latency, projection lag, and resource ceilings likewise require measured baselines; no additional numeric limit is silently invented.

Latency and cost improvements cannot weaken assessment validity, evidence quality, privacy, or replayability. The system must remain operable by 2-4 engineers. New infrastructure requires a demonstrated bottleneck, an owner, and an explicit migration cost.

## 19. Development, Staging, and Production Environments

Local, staging, and production are isolated environments with separate credentials, data stores, object storage, model configuration, and telemetry. Deployments are containerized on a managed PaaS from version-controlled configuration.

Development may use local S3-compatible storage and synthetic or approved de-identified data. Production data is never copied into development. Staging exercises database migrations, event compatibility, projection rebuild, deletion, provider fallback, and release rollback before production.

The cloud, PaaS, region, and exact Next.js mode are **Provisional**. The selected region must provide acceptable measured latency and lawful data handling for the target market.

## 20. Explicitly Rejected Architectural Patterns

The following cannot be introduced as implementation shortcuts:

- Allowing an LLM to directly mutate mastery, misconceptions, curriculum, role requirements, accepted evidence, or readiness.
- Using chat history or model memory as authoritative learner state.
- Storing only mutable current-state snapshots without reconstructable evidence events.
- Event-sourcing every application entity regardless of evidence or audit need.
- Static role-wide curricula or direct LLM-authored learner plans.
- Serving identical tasks, projects, or work simulations to different learners.
- Inferring mastery or readiness from module or content completion.
- Serving generated assessment items in high-stakes use before validation and calibration.
- Tight coupling to one LLM provider without an explicitly approved reason and migration decision.
- Hiding company-, industry-, geography-, or stack-specific requirements inside a generic `RoleProfile`.
- Treating an LLM evaluator as the sole judge of consequential readiness.
- Updating state from invalid, low-confidence, conflicting, or disputed evaluator output.
- Treating projections, dashboards, or reports as the source of truth.
- Unversioned prompts, rubrics, policies, algorithms, model routes, or role requirements.
- Executing learner-controlled code in the API or evidence worker process.
- Microservices or Kubernetes during validation.
- Copying production data into development.
- Public readiness certification or externally used automated readiness reports without human approval.
- Forking the engine for future school, organization, or employer shells.
