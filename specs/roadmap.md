# Validation Roadmap

## Purpose and Scope

This roadmap orders the smallest evidence-producing phases needed to validate the **AI Career Learning Platform**. It covers a relative 90-day platform-validation window. It is not a promise that every learner becomes ready for a complete role within 90 days.

The provisional Target is Junior Python Backend Engineer, entry-level or junior, for adults aged 18+ in Egypt and MENA who target local or English-speaking remote roles. The learner knows basic Python syntax and Git; the planning assumption for broader role preparation is 4-6 months. The initial Stack Overlay is Python, FastAPI, PostgreSQL, REST APIs, Git, automated testing, Docker, basic CI, debugging, documentation, and engineering communication. No Industry or Company Overlay is active.

`V00` and `V01` may narrow or replace this Target before curriculum or assessment production begins.

## Delivery Model

- Plan against 2-4 engineers, one learning designer, and at least two external practitioners. Capabilities have owners; named people and continuously staffed specialist roles are not assumed.
- Capability ownership covers learning engine and backend; product web experience; assessment, evaluation, data, and observability; infrastructure, security, and developer experience; and learning design, competency mapping, rubrics, and experiments. One person may own several capabilities.
- A normal implementation phase requires 2-5 engineering days. External recruitment, practitioner review, and 7- or 30-day observation windows are elapsed-time dependencies, not engineering estimates.
- Independent phases may overlap only after their entry conditions pass. Evidence dependencies may not be bypassed to preserve the 90-day window.
- `V18` must begin early enough to observe 30-day retention before `V22`. Otherwise the window extends or the final retention claim remains unproven.
- Each gate ends in **Continue**, **Revise**, **Narrow**, or **Stop**. A missed gate is never converted into assumed success.
- No mastery percentage is exposed before deterministic state ownership and assessment validity pass.
- No `ItemInstance` enters no-hint, delayed-retention, or transfer use unless its `ItemFamily` has `assessment_item` trust and the `ItemInstance` passes validation.
- No readiness report is used externally without human approval.
- School, minor-facing, employer, organization, marketplace, social, credentialing, native-mobile, and multi-role expansion are outside this sequence.


## Parallel Execution Lanes

The roadmap has two independently evidenced lanes:

- **Validation lane:** `V00`, `V01`, and later product, learning-science,
  production-hardening, and commercial validation gates. These phases decide
  whether a Target, learning claim, or role-specific system is authorized.
- **Foundation lane:** `F00`, `F01`, and later reversible technical-foundation
  phases. These phases establish only role-neutral capabilities that are
  reusable across plausible `V00` candidates.

A blocked validation phase does not automatically block an eligible foundation
phase. Foundation work cannot satisfy, infer, weaken, or bypass a validation
entry condition or evidence gate. Role-specific content, `RoleProfile`s,
competency graphs, learning logic, assessments, simulations, mastery, evidence
acceptance, readiness, and associated claims remain locked behind their existing
validation gates. Each lane records its own status, evidence, and gate decision.
Any foundation decision that would materially constrain role selection returns to
validation-lane review.
## Evidence Classes

- **Product validation:** proves that the workflow solves a bounded learner problem.
- **Learning-science validation:** tests diagnosis, mastery, retention, transfer, assessment validity, and prediction of realistic work performance.
- **Technical foundation:** establishes deterministic ownership, replay, provenance, and operability.
- **Production hardening:** establishes privacy, isolation, reliability, latency, and cost gates required for beta.
- **Commercial validation:** tests whether the bounded adult B2C outcome has a plausible market boundary without weakening evidence claims.
- **Commercial expansion:** occurs only in the evidence-conditional horizons after `V22`.


## Foundation Sequence

### F00 - Repository and Quality Foundation

**Class:** Technical foundation. **Effort:** 2-5 engineering days.

- **Objective:** Create a reproducible monorepo baseline for the approved web
  and API architecture.
- **Entry conditions:** The mission, technical constitution, and roadmap exist;
  FastAPI and Next.js are approved foundations; the scope is role-neutral; a
  clean automation branch is available; and no external `V00` evidence is
  required.
- **Outputs:** Backend and frontend application skeletons; deterministic local
  commands; formatting, linting, strict typing, testing, and coverage
  configuration; CI quality gates; line-ending policy; configuration-only health
  checks; and local developer documentation.
- **Non-goals:** Database schema, ORM, migrations, authentication, tenancy,
  object storage, background jobs, LLM gateway, role profiles, competency graphs,
  curriculum, assessment, tutoring, mastery, evidence acceptance, simulations,
  readiness, deployment vendor selection, or product claims.
- **Exit gate:** From a clean checkout, every declared local and CI check passes,
  API coverage is at least 95%, and independent review confirms that no
  role-specific or learning-state behavior was introduced.
- **Dependencies:** None. `F00` does not alter `V00`, unlock `V01`, or authorize
  any later validation or foundation phase.
- **Decision:** Continue only when the exit gate passes; Revise or Narrow the
  foundation scope on a failed check; Stop if the required foundation would
  constrain role selection or bypass a validation gate.

### F01 - Local Runtime Integration and API Contract Baseline

**Class:** Technical foundation. **Effort:** 2-5 engineering days.

- **Objective:** Establish one reproducible local API-and-web runtime with a
  mechanically checked, role-neutral health contract and an explicit
  unavailable-service experience.
- **Smallest scope:** Development process lifecycle plus `/health/live`,
  `/health/ready`, and `/openapi.json` only. The web availability surface uses
  `/health/live`; configuration readiness is not product or learner readiness.
- **Entry conditions:** `F00` passes; architecture and roadmap review confirm
  that F01 is reusable across every plausible `V00` candidate and does not
  constrain Target selection; the existing health endpoints and static web shell
  remain verified; and no external `V00` evidence is required.
- **Outputs:** One documented cross-platform, development-only root command that
  starts and cleanly stops the API and web with visible failure propagation and
  loopback defaults; validated server-only API-base configuration with no
  browser-exposed or user-controlled destination; a replaceable health adapter
  and accessible API-available/unavailable/invalid-response states; a canonical
  generated OpenAPI artifact, deterministic drift check, and health client/runtime
  validator derived from that contract rather than a handwritten response DTO;
  one deterministic cross-process smoke command invoked identically locally and
  by CI; focused unit, contract, lifecycle, and integration tests; and recorded
  startup, shutdown, smoke-time, dependency, storage, and process-resource deltas.
- **Non-goals:** Database, schema, ORM, migrations, authentication, identity,
  tenancy, domain or learner models, role or competency models, tutoring,
  assessment, mastery, curriculum, simulations, evidence acceptance, LLM calls,
  readiness, persistence, object storage, jobs, SSE, telemetry backend, general
  client SDK generation, browser-direct API calls, CORS or production routing,
  containers, deployment, service discovery, vendor selection, production
  process management, uptime claims, or product claims.
- **Exit gate:** From a clean checkout with locked dependencies, the root command
  starts and terminates both processes on Windows and the supported Linux CI
  runner without orphaning children; configuration and lifecycle failures are
  visible; the production web build passes with the API absent; the web reports
  API availability only after a bounded, non-cached response satisfies the
  OpenAPI-derived health contract and otherwise renders tested accessible failure
  states; contract drift fails deterministically; the same cross-process smoke
  passes locally and in CI without external services; every F00 quality gate
  still passes; resource deltas are recorded; and independent verification finds
  no forbidden domain behavior, readiness semantics, deployment choice, or
  change to `V00` or `V01`.
- **Dependencies:** `F00` only. F01 neither depends on nor satisfies `V00`, does
  not unlock `V01`, and does not authorize `V02` or later phases.
- **Decision:** Continue only when every exit condition passes. Revise failed
  lifecycle, contract, configuration, failure-state, or CI behavior. Narrow to
  the health-only boundary if broader client or networking infrastructure would
  be required. Stop if integration would constrain role selection, introduce
  domain state, select production topology, or bypass a validation gate.

### F02 - Cross-Process Correlation and Confidential Diagnostics Baseline

**Class:** Technical foundation. **Effort:** 2-5 engineering days.

- **Objective:** Establish vendor-neutral W3C trace correlation and allowlisted
  structured diagnostics across the existing server-rendered web-to-API health
  transaction without adding product telemetry, persistent state, or an
  external telemetry service.
- **Smallest scope:** The existing Next.js server-to-FastAPI `/health/live`
  transaction only: safe trace-context creation and propagation, isolated API
  request context, confidential fixed-vocabulary diagnostic events, and one
  cross-process verification gate. The browser receives no trace context or
  diagnostic payload.
- **Entry conditions:** `F01` passes; OpenTelemetry-compatible instrumentation
  and structured diagnostics remain approved, role-neutral boundaries; an
  architecture review confirms that this scope is reusable across every
  plausible `V00` candidate; any instrumentation dependency preserves W3C
  interoperability and a replaceable exporter boundary; and no external `V00`
  evidence is required.
- **Outputs:** A recorded dependency and ownership decision with requirement
  fit, operational cost, failure behavior, and replacement path; strict W3C
  context validation and safe root creation; API middleware with concurrency
  isolation and cleanup; an allowlisted JSON diagnostic-event contract that
  rejects free-form sensitive fields; server-only trace propagation and bounded
  outcome/timing diagnostics around the existing health adapter; adversarial
  confidentiality, malformed-context, isolation, and duplicate-instrumentation
  tests; one identical local/CI cross-process diagnostic check; and dependency,
  startup, shutdown, process, memory, event-volume, byte-volume, and fixed-sample
  health-latency observations.
- **Non-goals:** PostgreSQL, ORM, migrations, schemas, persistence, events,
  outbox, replay, projections, jobs, authentication, authorization, domain or
  learner identifiers, role or learning state, product analytics, audit
  history, operational budgets, `V17A` evidence, browser or client telemetry,
  an exporter, telemetry backend or vendor, network egress, monitoring,
  alerting, production sampling or retention policy, deployment, LLM access, or
  privacy/compliance approval.
- **Exit gate:** One real F01 health transaction produces matching valid trace
  identifiers and distinct nonzero spans in web and API diagnostics; absent or
  malformed incoming context creates a safe new root; concurrent and completed
  requests cannot leak context; test canaries placed in request metadata,
  configuration, response detail, and failure text never appear in logs or
  browser output; every emitted field belongs to the fixed allowlist and no raw
  URL, query, header, body, exception text, or environment value is logged;
  diagnostic event count and byte volume are bounded; no exporter, persistent
  diagnostic store, network egress, product metric, audit claim, or domain
  identifier exists; all F00/F01 contract, timeout, confidentiality, process,
  cleanup, coverage, Windows, and exact Ubuntu CI gates remain green; resource
  deltas are recorded without inventing a platform budget; and independent
  verification finds no `V00`, `V01`, `V17A`, product, learner, evidence, or
  readiness leakage.
- **Dependencies:** `F01` only. F02 neither depends on nor satisfies `V00`, does
  not unlock `V01`, does not authorize `V02` or `V17A`, and makes no privacy or
  production-operability claim.
- **Decision:** Continue only when every exit condition passes. Revise context,
  confidentiality, isolation, duplication, or resource failures. Narrow back to
  an API-only confidential-diagnostics amendment if cross-process propagation
  would require browser telemetry, production topology, or a backend choice.
  Stop if useful diagnostics require raw sensitive content, product/domain
  identifiers, a vendor commitment, or a validation-gate bypass.

## Initial Validation Sequence

### V00 - Candidate Role Evidence

**Class:** Product validation. **Effort:** 3-5 engineering days.

- **Objective:** Test whether the provisional role is the strongest feasible first validation Target.
- **Smallest scope:** Compare it with credible alternative technical roles using current demand, baseline stability, assessment and simulation feasibility, practitioner and learner access, and expected infrastructure and evaluation cost.
- **Outputs:** Source-backed comparison, complete Target tuples, unresolved assumptions, recommended candidate, and rejection reasons.
- **Entry conditions:** Adult B2C boundary and validation claim are approved.
- **Acceptance criteria:** Every candidate resolves role, seniority, labor market, learner baseline, timeline, Overlays, exclusions, and evidence feasibility.
- **Evidence gate:** The chosen candidate has sufficient demand, a stable bounded baseline, an objectively assessable slice, a realistic simulation path, acceptable expected cost, at least two qualified practitioners, and a real 20-50 learner recruitment channel.
- **Dependencies:** None.
- **Non-goals:** Curriculum or assessment production, a role marketplace, or preserving Junior Python Backend Engineer by default.
- **Decision:** Continue with the strongest supported candidate; Revise weak evidence; Narrow role or market scope; Stop if no candidate passes.

### V01 - Role Selection and Proof Contract

**Class:** Product validation. **Effort:** 3-5 engineering days.

- **Objective:** Approve one named, versioned `RoleProfile` and a bounded proof contract.
- **Smallest scope:** Define the selected Target, a coherent 40-80-node proof slice, one realistic work outcome, and at least one `WorkSimulationBlueprint` and rubric.
- **Outputs:** Versioned `RoleProfile`, scope and exclusions, proof-slice definition, learner baseline, simulation Blueprint and rubric, practitioner decisions, and recruitment evidence.
- **Entry conditions:** `V00` identifies a viable candidate; at least two qualified practitioners and a real recruitment channel are available.
- **Acceptance criteria:** The slice includes conceptual knowledge, tool use, debugging or problem solving, and engineering communication or decision explanation. The `RoleProfile` defines outcomes, not a syllabus.
- **Evidence gate:** At least two practitioners approve the role scope, proof slice, realistic outcome, simulation Blueprint, and rubric.
- **Dependencies:** `V00`.
- **Non-goals:** Complete-role authoring, a fixed curriculum, Industry or Company Overlays, or item volume.
- **Decision:** Continue only with approval; Revise the contract; Narrow the slice; or replace/Stop the candidate before content production.

### V02 - Versioned Domain and State Contracts

**Class:** Technical foundation. **Effort:** 3-5 engineering days.

- **Objective:** Establish deterministic ownership and versioned contracts before tutor sophistication.
- **Smallest scope:** Define contracts for role, graph, attempts, verdicts, hints, assessments, learner-state transitions, plans, `ItemFamily`, `ItemInstance`, Blueprints, work Instances, structured evidence, reviewer decisions, and disputes.
- **Outputs:** Versioned schemas, state-transition policies, ownership boundaries, correlation and causation conventions, and compatibility rules.
- **Entry conditions:** `V01` passes.
- **Acceptance criteria:** Every deterministic transition names its input evidence and applicable policy, model, prompt, rubric, item, Blueprint, algorithm, `RoleProfile`, and `LearnerPlanVersion`. LLM contracts expose no authoritative mutation command.
- **Evidence gate:** Architecture review traces every proof claim to structured inputs and one deterministic owner.
- **Dependencies:** `V01`.
- **Non-goals:** User-facing tutoring, full persistence, or implementation of every long-term entity.
- **Decision:** Continue when ownership is unambiguous; Revise schemas; Narrow the first event set; Stop if authoritative state still depends on chat history or model judgment.

### V03 - Evidence Ledger, Outbox, and Replay

**Class:** Technical foundation. **Effort:** 4-5 engineering days.

- **Objective:** Make evidence-bearing operations durable, idempotent, and reconstructable.
- **Smallest scope:** Append-only PostgreSQL events, transactional outbox, one replay worker, and representative evidence projections.
- **Outputs:** Event ledger, outbox, idempotent consumers, replay command, projection checkpoints, and audit correlations.
- **Entry conditions:** `V02` contracts are approved.
- **Acceptance criteria:** Duplicate delivery creates no duplicate state; interrupted processing resumes safely; identical events and versions reproduce identical projections; non-evidence state remains conventionally transactional.
- **Evidence gate:** Fault and replay tests recover a known projection exactly and expose failures rather than returning silent empty or current-only results.
- **Dependencies:** `V02`.
- **Non-goals:** Event-sourcing every entity, a dedicated broker, workflow engine, or microservices.
- **Decision:** Continue on exact replay; Revise event or idempotency contracts; Narrow projections; Stop claims work if evidence cannot be reconstructed.

### V04 - Proof Competency Graph

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Encode the approved proof slice as a traceable outcome graph.
- **Smallest scope:** Store the 40-80 nodes and typed relational edges in PostgreSQL with source, confidence, scope, effective date, reviewer, and expiry metadata.
- **Outputs:** Versioned `CompetencyGraph`, recursive prerequisite queries, graph repository interface, misconception seed taxonomy, and practitioner delta report.
- **Entry conditions:** `V01` and `V02` pass.
- **Acceptance criteria:** The graph supports prerequisite, component, and transfer relationships; unknowns remain explicit; Stack requirements remain an Overlay rather than hidden common-core additions.
- **Evidence gate:** At least two practitioners confirm that the implemented graph preserves the approved outcome and proof-slice boundaries.
- **Dependencies:** `V01`, `V02`.
- **Non-goals:** A graph database, generalized marketplace, complete role, or fixed learner sequence.
- **Decision:** Continue on credible traceability; Revise nodes or edges; Narrow the slice; Stop if practitioners cannot agree on a bounded baseline.

### V05 - Blueprint and Assessment Contracts

**Class:** Learning-science validation. **Effort:** 4-5 engineering days.

- **Objective:** Establish asset trust before generative scale or assessment claims.
- **Smallest scope:** Versioned `TaskBlueprint` and `WorkSimulationBlueprint` schemas, `ItemFamily` contracts, trust transitions, core validators, protected checkpoint families, and rubric invariants.
- **Outputs:** Approved Blueprint and `ItemFamily` schemas, assistance policies, solver/test and constraint validators, leakage and safety rules, rubric-coverage checks, exposure controls, and separate item and simulation trust paths.
- **Entry conditions:** `V04` passes.
- **Acceptance criteria:** Neither an `ItemFamily` nor a Blueprint can bypass its trust path or per-Instance validation; practice, assessment, simulation-validation, and complete-readiness trust levels remain distinct; protected cases cannot leak into tutoring or practice.
- **Evidence gate:** The learning or assessment owner and practitioners approve competency coverage, rubric equivalence, trust rules, and validation failures.
- **Dependencies:** `V04`.
- **Non-goals:** Large-scale generated content, assessment or readiness-grade claims, or assuming family or Blueprint trust makes an individual Instance valid.
- **Decision:** Continue on valid contracts; Revise schemas; Narrow measured competencies; Stop high-stakes work if validity cannot be defended.

### V06 - Controlled Evaluator Dataset

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Create a frozen basis for evaluator and tutor-policy regression.
- **Smallest scope:** 20-30 expert-labeled evaluator and tutoring cases covering correct, incorrect, alternative-valid, misconception-bearing, low-confidence, conflicting, and disputed responses.
- **Outputs:** Immutable versioned dataset, labels and rationales, category balance, held-out cases, and failure taxonomy.
- **Entry conditions:** `V05` passes and reviewers are available.
- **Acceptance criteria:** Labels are fixed before evaluator scoring; protected cases are not used as prompts or learner practice; disagreement among labelers is retained.
- **Evidence gate:** The assessment owner and practitioners approve labels, sampling, held-out cases, and failure categories.
- **Dependencies:** `V05`.
- **Non-goals:** Large item volume, production mastery updates, or post-hoc relabeling to improve a score.
- **Decision:** Continue on an auditable controlled set; Revise ambiguous cases before scoring; Narrow eligible response types; Stop if reliable labels cannot be established.

### V07 - Evaluator Gate

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Determine whether structured evaluator evidence may enter deterministic learner state.
- **Smallest scope:** Schema-constrained step grading against `V06`, including confidence, conflict, and dispute handling.
- **Outputs:** Versioned evaluator, category-level disagreement report, confidence and dispute rules, and replayable verdict records.
- **Entry conditions:** `V03` and `V06` pass.
- **Acceptance criteria:** Every failure is categorized; disputed verdicts are excluded from state; identical evidence and evaluator versions replay identically.
- **Evidence gate:** Step grading reaches at least 90% agreement on the controlled test set, accompanied by per-category results and failure analysis.
- **Dependencies:** `V03`, `V06`.
- **Non-goals:** Practitioner readiness agreement, automatic dispute resolution, or treating fluent model output as accepted evidence.
- **Decision:** Continue only at or above 90%; Revise evaluator or rubric without changing observed labels; Narrow evaluator-eligible cases; Stop evaluator-driven updates if the gate remains unmet.

### V08 - Minimal Tutoring Vertical Slice

**Class:** Product validation. **Effort:** 4-5 engineering days.

- **Objective:** Prove the smallest learner-facing teach-and-reassess loop without surrendering state ownership.
- **Smallest scope:** A few representative proof nodes using verified-practice `ItemInstance`s, REST/SSE, tutor-move state machine, hint ladder, step capture, evaluator call, and event logging.
- **Outputs:** Learner attempt flow, streamed response, policy-selected tutor moves, hint records, traceable transcript, and latency baseline.
- **Entry conditions:** `V03`, `V05`, and `V07` pass.
- **Acceptance criteria:** Attempt, verdict, move, learner continuation, and evidence event complete end to end; the LLM only proposes moves; provider failure cannot corrupt evidence.
- **Evidence gate:** Golden transcript and dogfood review show observable failures, policy-controlled hints, and no model-owned mastery or sequencing.
- **Dependencies:** `V03`, `V05`, `V07`.
- **Non-goals:** Sophisticated persona, readiness reporting, mastery dashboard, 30-node coverage, or complete role coverage.
- **Decision:** Continue on a traceable usable loop; Revise tutor policy; Narrow move types; Stop progression if failures cannot be bounded.

### V08R - Verified Coverage Tranche (Repeatable)

**Class:** Product and learning-science validation. **Effort:** 2-5 engineering days per tranche.

- **Objective:** Expand only validated practice and tutoring coverage in bounded increments.
- **Smallest scope:** One reviewable tranche of additional proof nodes, verified practice items, hint ladders, validators, and golden traces.
- **Outputs:** Versioned `ItemFamily` and `ItemInstance` records, validation records, node-coverage delta, collision results, and failure report.
- **Entry conditions:** `V08` passes; applicable `V05` validators exist.
- **Acceptance criteria:** No `generated_untrusted` item is served; every `ItemFamily` has the required trust and every `ItemInstance` passes uniqueness and validation rules; tutor behavior remains within the accepted policy.
- **Evidence gate:** Each tranche passes content, solver/test, rubric, safety, leakage, evaluator, and regression review. Before beta, cumulative end-to-end coverage reaches at least 30 proof nodes and several hundred verified practice items.
- **Dependencies:** `V05`, `V08`.
- **Non-goals:** Unreviewed content volume, high-stakes promotion by launch pressure, or finishing the complete role.
- **Decision:** Continue with another tranche only when quality holds; Revise failed families; Narrow node coverage; Stop scaling if validation cost is unacceptable.

### V09 - Deterministic Learner State

**Class:** Technical foundation. **Effort:** 4-5 engineering days.

- **Objective:** Implement authoritative mastery, misconception, forgetting, and assessment-state transitions.
- **Smallest scope:** Proof-slice rules using accepted evidence, hint discounts, dispute state, decay inputs, and review scheduling.
- **Outputs:** Deterministic services, policy versions, projections, and property, replay, branch, and mutation tests.
- **Entry conditions:** `V03` and `V07` pass.
- **Acceptance criteria:** LLM output cannot write state directly; invalid or disputed verdicts have no state effect; identical evidence and versions reproduce state; synthetic histories create no impossible mastery jumps.
- **Evidence gate:** Replay, idempotency, monotonic-evidence, and policy-boundary tests pass with at least 95% line coverage for these deterministic services.
- **Dependencies:** `V03`, `V07`.
- **Non-goals:** A final psychometric model, mastery display, or readiness inference.
- **Decision:** Continue on reproducible behavior; Revise rules; Narrow eligible evidence; Stop mastery claims if ownership is incomplete.

### V10 - Baseline Diagnosis and Gap Map

**Class:** Product validation. **Effort:** 3-5 engineering days.

- **Objective:** Produce a role-relevant diagnosis from evidence rather than self-report.
- **Smallest scope:** One versioned baseline diagnostic and proof-slice gap map for controlled learners.
- **Outputs:** Diagnostic `ItemInstance`s, accepted evidence, gap map, uncertainty representation, and comparison protocol against self-report and a linear placement quiz.
- **Entry conditions:** `V05`, `V07`, and `V09` pass.
- **Acceptance criteria:** Self-report may prioritize assessment but cannot grant mastery; every gap maps to graph nodes and evidence; controlled or uncalibrated diagnostic output cannot update validation-cohort state; uncertainty requests stronger evidence.
- **Evidence gate:** Under criteria fixed before testing, practitioner review finds meaningful role-relevant signal beyond the comparison baselines, with uncertainty reported.
- **Dependencies:** `V04`, `V05`, `V07`, `V09`.
- **Non-goals:** Complete-role diagnosis, generic aptitude testing, or readiness conclusions.
- **Decision:** Continue on useful gap signal; Revise design; Narrow measured nodes; Stop personalized planning if diagnosis adds no defensible signal.

### V11 - Learner-Specific Curriculum Compilation

**Class:** Technical foundation. **Effort:** 4-5 engineering days.

- **Objective:** Compile and recompute a versioned route for one learner from evidence and constraints.
- **Smallest scope:** Initial plan plus replanning for mastery, misconception, forgetting, failed performance, available time, Target change, role or policy version change, and proof-slice evidence.
- **Outputs:** Deterministic `CurriculumPlanner`, stable pseudonymous learner-bound plan seed, `LearnerPlanVersion`, readable delta, and evidence remapping for `RoleProfile` changes.
- **Entry conditions:** `V04`, `V09`, and `V10` pass.
- **Acceptance criteria:** Identical learner-bound inputs reproduce the same plan; same-role learners receive non-identical plans through deterministic selection among policy-equivalent routes; differences never weaken requirements, prerequisites, evidence thresholds, or difficulty; prior evidence survives replanning.
- **Evidence gate:** The learning designer and practitioners approve sample plans and deltas as plausible responses to the recorded evidence.
- **Dependencies:** `V04`, `V09`, `V10`.
- **Non-goals:** Static role curriculum, LLM-owned sequencing, generalized optimization, or identical routes for convenience.
- **Decision:** Continue on reproducible differentiation; Revise policy; Narrow supported constraints; Stop personalization claims if plans do not respond meaningfully.

### V12 - Independent Performance Gate

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Prevent hinted or fluent performance from being called mastery.
- **Smallest scope:** Tutor-silent checkpoints, reasoning or explain-back checks, scheduled hint withdrawal, and protected assessment `ItemInstance`s.
- **Outputs:** No-hint mode, reasoning evidence, assistance policy, protected assessment selection, and rules requiring independent evidence.
- **Entry conditions:** `V05`, `V09`, and `V11` pass.
- **Acceptance criteria:** Hinted success alone cannot satisfy mastery; live evidence uses only protected, validated `ItemInstance`s from `ItemFamily` records at `assessment_item` trust, and the mode remains blocked until that trust level exists; disputed reasoning is excluded.
- **Evidence gate:** Controlled cases prove that high hinted accuracy with weak no-hint or reasoning performance remains unverified.
- **Dependencies:** `V05`, `V09`, `V11`.
- **Non-goals:** Mastery percentages, engagement rewards, or conversational fluency as reasoning.
- **Decision:** Continue when dependency is detectable; Revise withdrawal checks; Narrow mastery-eligible nodes; Stop claims that cannot require independent performance.

### V13 - Retention and Transfer Infrastructure

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Make delayed-retention and unseen-transfer observations schedulable, protected, and auditable.
- **Smallest scope:** Immediate, 7-day, and 30-day probe scheduling plus unseen near-transfer and applicable far-transfer `ItemInstance` delivery for the proof slice.
- **Outputs:** Retention scheduler, decay and re-verification rules, contamination controls, transfer engine, and longitudinal event contracts.
- **Entry conditions:** `V12` passes and the delivery plan can begin observations early enough to complete the 30-day window.
- **Acceptance criteria:** Timing is auditable; protected items are not tutored; transfer surfaces are unseen; mastery remains provisional or decays until required re-verification.
- **Evidence gate:** Controlled scheduling, contamination, replay, and eligibility tests pass. No retention or transfer outcome is claimed until `V19` observes the preregistered learner evidence.
- **Dependencies:** `V05`, `V09`, `V12`.
- **Non-goals:** Proving retention before elapsed observations, treating immediate post-test gains as retention, or using familiar practice forms as transfer.
- **Decision:** Continue when observation infrastructure is trustworthy; Revise probes; Narrow unsupported competencies; Stop retention claims if valid observations cannot be produced.

### V14 - Unique Work Instantiation

**Class:** Product validation. **Effort:** 4-5 engineering days.

- **Objective:** Produce unique learner tasks and unseen work simulations while preserving shared validity.
- **Smallest scope:** Learner-bound task and work-simulation Instances from approved Blueprints, with an isolated runner where code executes.
- **Outputs:** Seeds and parameters, learner and plan bindings, hidden changes or tests, assistance policies, semantic fingerprints, a history-wide non-identifying collision index, and validation records.
- **Entry conditions:** `V05`, `V11`, and the `V13` infrastructure gate pass; the runner boundary is approved where applicable.
- **Acceptance criteria:** Every served Instance is distinct from all retained prior Instances across learners and cohorts; exact and near duplicates are rejected; each Instance preserves competency coverage, difficulty, rubric, and assistance policy.
- **Evidence gate:** At least two practitioners approve pilot Instances for realism, equivalence, uniqueness, and the named work outcome; collision tests cover equivalent as well as different learner profiles.
- **Dependencies:** `V05`, `V11`, `V13`.
- **Non-goals:** A large simulation catalogue, identical capstones, unbounded generation, complete projects, or readiness conclusions.
- **Decision:** Continue on valid diversity; Revise parameters or validators; Narrow scenario variation; Stop personalization claims if uniqueness destroys comparability.

### V15 - Artifact Provenance, Modification, and Defense

**Class:** Product validation. **Effort:** 3-5 engineering days.

- **Objective:** Establish that submitted work belongs to the learner and can be explained, modified, debugged, and defended.
- **Smallest scope:** Checkpointed artifact history, assistance disclosure, immutable attachments, one hidden modification request, and one oral or written defense flow.
- **Outputs:** Provenance record, artifact versions, assistance ledger, defense and modification evidence, reviewer workflow, and dispute record.
- **Entry conditions:** `V03` and `V14` pass.
- **Acceptance criteria:** Missing provenance or prohibited answer-level assistance blocks evidence acceptance; revisions remain traceable; reviewer decisions carry identity, rationale, and version context.
- **Evidence gate:** Practitioner review distinguishes unsupported polished output from independently explained and modified work.
- **Dependencies:** `V03`, `V14`.
- **Non-goals:** Public portfolio, automated certification, unrestricted transcript access, or artifact appearance as proof.
- **Decision:** Continue on defensible provenance; Revise capture rules; Narrow eligible artifacts; Stop work-evidence claims if ownership cannot be established.

### V16 - Partial Evidence and Validation Protocol

**Class:** Learning-science validation. **Effort:** 3-5 engineering days.

- **Objective:** Compute proof-slice evidence deterministically and preregister both learning analysis and blinded practitioner comparison.
- **Smallest scope:** A replayable evidence projection plus protocols for independence, retention, transfer, hint dependency, missingness, attrition, and practitioner agreement.
- **Outputs:** `partial_profile_evidence` report; mandatory gaps, stale or disputed evidence, simulation status, confidence and uncertainty; preregistered learning criteria; and preregistered practitioner metric, sampling, minimum sample size, threshold, disagreement handling, and decision rules.
- **Entry conditions:** `V09`, `V12`, `V13`, `V14`, and `V15` pass.
- **Acceptance criteria:** Completion cannot substitute for evidence; a strong artifact cannot offset a mandatory gap; identical inputs reproduce the result; learning and practitioner criteria are fixed before beta outcomes; no generic "job ready" state is emitted.
- **Evidence gate:** The assessment owner and practitioners approve both protocols before beta outcomes are examined. The 90% evaluator threshold is not reused automatically.
- **Dependencies:** `V09`, `V12`, `V13`, `V14`, `V15`.
- **Non-goals:** Complete-role readiness, hiring prediction, external certification, or post-hoc threshold selection.
- **Decision:** Continue with preregistered protocols; Revise before outcomes; Narrow claim or sample; Stop comparison if credible criteria cannot be defined.

### V16A - Identity, Authorization, and Environment Isolation

**Class:** Production hardening. **Effort:** 2-5 engineering days.

- **Objective:** Establish adult-account ownership and isolate execution environments before beta.
- **Smallest scope:** Managed OIDC integration, explicit learner/reviewer/admin permissions, object access, and separate local, staging, and production identities and stores.
- **Outputs:** Identity mapping, authorization policy, access audits, environment inventory, and isolation tests.
- **Entry conditions:** `V02` and the initial deployment shape are stable enough to test.
- **Acceptance criteria:** Cross-learner access is denied; jobs recheck authorization context; production credentials and data cannot enter development; reviewer access is purpose-scoped.
- **Evidence gate:** Authorization, object-access, secret-isolation, and environment-boundary tests pass with no critical defect.
- **Dependencies:** `V02`, `V03`.
- **Non-goals:** Organizations, delegated administration, employer access, or production-data copies.
- **Decision:** Continue on demonstrated isolation; Revise permissions; Narrow exposed workflows; Stop beta if ownership cannot be enforced.

### V16B - Privacy and Data Lifecycle

**Class:** Production hardening. **Effort:** 2-5 engineering days.

- **Objective:** Make beta data handling reviewable and enforce the approved retention boundary.
- **Smallest scope:** Raw-transcript separation, 30-day default retention, ingestion redaction, account export, deletion, and artifact lifecycle.
- **Outputs:** Data-flow inventory, privacy review, retention job, export package, deletion workflow, redaction tests, and deletion audit.
- **Entry conditions:** `V03` and `V16A` pass; vendors and data flows are known enough for review.
- **Acceptance criteria:** Structured evidence survives only as approved; raw text is not retained by convenience; deletion cannot rehydrate PII through replay; telemetry is redacted at ingestion.
- **Evidence gate:** Legal and privacy review is complete and no critical retention, export, deletion, redaction, or data-residency issue remains.
- **Dependencies:** `V03`, `V16A`.
- **Non-goals:** A named compliance claim, minors, or indefinite transcript storage.
- **Decision:** Continue on approved handling; Revise flows or duration; Narrow collected data; Stop beta if lawful handling cannot be demonstrated.

### V17A - Operational Measurement and Budgets

**Class:** Production hardening. **Effort:** 3-5 engineering days.

- **Objective:** Measure latency, cost, provider, job, projection, replay, and tutor-policy behavior before beta.
- **Smallest scope:** OpenTelemetry correlation and the required operational metrics across one end-to-end learner flow and representative background work.
- **Outputs:** p50/p95 latency, end-to-end turn latency, session and competency cost baselines, schema and evaluator failures, fallback, retry/dead-letter, projection-lag, replay-failure, and tutor-move reports.
- **Entry conditions:** `V08`, `V09`, `V11`, and representative jobs are operational.
- **Acceptance criteria:** Every metric traces to session, attempt, evaluator call, transition, plan, and job; missing or sampled telemetry cannot be mistaken for zero; alternate provider adapter contract tests pass.
- **Evidence gate:** p95 first-token latency is below 2.5 seconds, and session, learner, and verified-competency cost ceilings are measured and approved before beta.
- **Dependencies:** `V08`, `V09`, `V11`.
- **Non-goals:** The mature sub-2-second target, a telemetry vendor commitment, or cost savings that weaken evidence.
- **Decision:** Continue on observable acceptable operation; Revise routing or instrumentation; Narrow provider or feature scope; Stop beta if cost or latency is unacceptable.

### V17B - Beta-Entry Gate

**Class:** Production hardening. **Effort:** 3-5 engineering days.

- **Objective:** Prove that beta operations cannot silently corrupt evidence.
- **Smallest scope:** Critical replay, idempotency, load, fault, provider-failure, storage, deletion, isolation, item-trust blocking, and evidence-bearing work-Instance checks.
- **Outputs:** Gate report, test evidence, dead-letter and replay results, approved beta asset inventory, reviewer roster, and recruitment-channel confirmation.
- **Entry conditions:** `V07`-`V17A` pass; cumulative `V08R` coverage meets its beta gate; practitioners and a 20-50 learner channel remain real.
- **Acceptance criteria:** Approved coverage, branch, mutation, property, contract, load, and fault tests pass; provider failure degrades capability without accepting evidence; high-stakes item delivery remains blocked until `V17C`; every evidence-bearing simulation derives from an `expert_reviewed` or higher Blueprint and passes Instance validation.
- **Evidence gate:** Privacy review, preregistration, reviewer capacity, recruitment access, latency and cost ceilings, critical tests, and asset approvals are all present. No beta learner is recruited before this gate passes.
- **Dependencies:** `V07` through `V17A`, including `V08R`, `V16A`, and `V16B`.
- **Non-goals:** Public launch, multi-region operation, Kubernetes, a dedicated broker, or scaling beyond beta.
- **Decision:** Continue only on a complete gate; Revise defects; Narrow cohort, content, or provider scope; Stop beta if evidence integrity or acceptable cost cannot be achieved.

### V17C - Assessment Calibration Gate

**Class:** Learning-science validation. **Effort:** 2-5 engineering days plus consented response-data elapsed time.

- **Objective:** Earn high-stakes item trust before no-hint, retention, or transfer evidence is accepted.
- **Smallest scope:** Enroll a consented calibration-only subgroup through the secured recruitment channel; expose protected `beta_item` families only in non-high-stakes research or practice; compute exposure, difficulty, discrimination, leakage, and drift; and validate unique `ItemInstance`s.
- **Outputs:** Calibration-sample provenance, versioned item statistics, contamination records, promotion or demotion decisions, protected `assessment_item` inventory, and unresolved coverage gaps.
- **Entry conditions:** `V17B` passes; the recruitment channel can supply a calibration-only subgroup; consent, privacy, and exposure controls are active; preregistered promotion and sample-sufficiency rules exist.
- **Acceptance criteria:** Exposed forms and contaminated families are excluded from later assessment for the same learner; a calibration respondent may enter `V18` only on unexposed eligible families and is analyzed separately; family statistics and `ItemInstance` validation pass; insufficient data never becomes an assessment item by deadline exception.
- **Evidence gate:** The item families required for baseline, no-hint, 7-day, 30-day, and transfer evidence reach `assessment_item` trust under preregistered rules. Otherwise the relevant beta evidence remains blocked.
- **Dependencies:** `V05`, `V08R`, `V16`, `V17B`.
- **Non-goals:** Counting calibration-only respondents as validation learners without independent eligibility, treating expert review alone as calibration, weakening trust thresholds, or producing content volume.
- **Decision:** Continue when the protected inventory is sufficient; Revise or extend calibration; Narrow assessed nodes; Stop high-stakes evidence collection if trust cannot be earned.

### V18 - Closed Beta Launch

**Class:** Product validation. **Effort:** 3-5 engineering days plus cohort elapsed time.

- **Objective:** Start an instrumented adult B2C validation with the approved Target segment.
- **Smallest scope:** Enroll 20-50 suitable validation learners; run consent, baseline diagnosis, learner-specific planning, tutoring, and a visible weekly role-gap plan.
- **Outputs:** Eligible cohort, versioned baselines and plans, protected assessment assignments, exposure exclusions, privacy-safe analytics, recovery paths, and review queue.
- **Entry conditions:** `V17C` passes with enough elapsed time remaining for 30-day probes.
- **Acceptance criteria:** Learners match the baseline or are analyzed separately; calibration respondents count only if independently eligible and assigned unexposed families; every plan is learner-specific; all evidence traces to approved versions; failures and missing data are visible.
- **Evidence gate:** Cohort and instrumentation audits pass, and no unapproved assessment or simulation reaches a learner.
- **Dependencies:** `V17C`.
- **Non-goals:** Public launch, employment guarantee, complete role, addictive gamification, or interpreting enrollment as efficacy.
- **Decision:** Continue on trustworthy data; Revise onboarding; Narrow cohort or slice; Stop enrollment on evidence, privacy, or safety failure.

### V19 - Longitudinal Learning Evidence

**Class:** Learning-science validation. **Effort:** 2-5 engineering days of analysis and operations plus 30 elapsed days.

- **Objective:** Measure gap closure, independence, retention, transfer, misconception change, and hint dependency.
- **Smallest scope:** Analyze beta attempts, no-hint and reasoning checks, immediate, 7-day, and 30-day probes, unseen transfer, and tutor-withdrawal performance.
- **Outputs:** Preregistered metric report, attrition and missingness analysis, uncertainty, failure traces, and item/evaluator drift report.
- **Entry conditions:** `V16` is preregistered, `V17C` provides trusted assessment families, `V18` produces eligible observations, and `V13` schedules complete.
- **Acceptance criteria:** Immediate and delayed results remain separate; hinted and no-hint outcomes remain separate; transfer was unseen; disputed evidence is excluded.
- **Evidence gate:** Results meet or fail the preregistered learning criteria with stated uncertainty. Week-two return is reported against the strategy's 50% gate but is not learning proof.
- **Dependencies:** `V13`, `V16`, `V17C`, `V18`.
- **Non-goals:** Universal efficacy, engagement optimization, causal hiring claims, or hiding failed probes in aggregate mastery.
- **Decision:** Continue on credible independent evidence; Revise pedagogy or measurement; Narrow competencies or claims; Stop mastery claims if gains disappear under withdrawal or delay.

### V20 - Unseen Simulation and Blinded Review

**Class:** Learning-science validation. **Effort:** 3-5 engineering days plus reviewer elapsed time.

- **Objective:** Test whether system evidence predicts realistic work performance.
- **Smallest scope:** One unique unseen work-simulation Instance per eligible learner, no answer-level tutoring, and blinded practitioner review of the preregistered sample.
- **Outputs:** Validated Instances, artifacts and provenance, modification and defense evidence, blinded ratings, disagreement cases, calibration analysis, and a simulation-Blueprint trust decision.
- **Entry conditions:** `V14`-`V16` pass and eligible beta learners have sufficient proof-slice evidence.
- **Acceptance criteria:** Reviewers are blind to system conclusions; Instances remain rubric-equivalent; evidence and assistance are traceable; disagreement remains visible; pilot or calibrated simulation evidence remains `partial_profile_evidence` and cannot imply complete-role readiness.
- **Evidence gate:** System evidence meets or fails the preregistered practitioner-agreement threshold and uncertainty rule, with failure categories reported separately.
- **Dependencies:** `V14`, `V15`, `V16`, `V18`.
- **Non-goals:** Complete-role or every-employer readiness, employment prediction, or substituting evaluator agreement for practitioner agreement.
- **Decision:** Continue on preregistered agreement; Revise rubric or policy; Narrow slice or claim; Stop readiness inference if realistic performance is not predicted.

### V21 - Commercial Boundary Signal

**Class:** Commercial validation. **Effort:** 2-3 engineering days.

- **Objective:** Test whether adults value the bounded outcome without changing the learning claim.
- **Smallest scope:** Measure recruitment conversion, retention, willingness to pay, and pricing response around verified role progress rather than content access.
- **Outputs:** Commercial-signal report, acquisition assumptions, stated and observed willingness-to-pay evidence, retention caveats, and cost comparison.
- **Entry conditions:** `V18` is instrumented and `V17A` cost baselines exist.
- **Acceptance criteria:** Learning, product, and commercial metrics remain separate; hiring outcomes are labeled non-causal downstream signals.
- **Evidence gate:** The report states whether a plausible adult B2C boundary exists at measured cost without weakening evidence gates or making hiring promises.
- **Dependencies:** `V17A`, `V18`.
- **Non-goals:** Employer sales, organizations, placement guarantees, credential pricing, or engagement as learning proof.
- **Decision:** Continue on a plausible offer; Revise pricing or positioning; Narrow the segment; Stop expansion if economics require invalid claims.

### V22 - Instrumented Validation Decision

**Class:** Product validation. **Effort:** 2-3 engineering days.

- **Objective:** Decide whether evidence earns expansion beyond the proof slice.
- **Smallest scope:** One auditable memo covering role validity, diagnosis, learning, retention, transfer, unique work, simulation prediction, technical reliability, privacy, cost, latency, commercial signal, uncertainty, and failures.
- **Outputs:** Evidence index, decision memo, unresolved risks, explicit decision, and next-horizon entry conditions.
- **Entry conditions:** `V19`, `V20`, and `V21` complete; no material gate is silently omitted.
- **Acceptance criteria:** Every conclusion traces to versioned evidence; negative and inconclusive results remain visible; product, learning-science, technical, production, and commercial findings remain distinct.
- **Evidence gate:** Evidence supports, or explicitly fails to support, this bounded claim:

  > For a validated competency slice of the selected named role, the system can diagnose a learner's gaps, compile and update a learner-specific curriculum, teach what is missing, verify independent retention and transfer, generate a unique realistic work simulation, and produce evidence that meaningfully predicts practitioner-rated performance with stated uncertainty.

- **Dependencies:** All preceding phases.
- **Non-goals:** Universal or complete-role readiness, employment causation, public credentialing, or expansion by schedule.
- **Decision:** Continue toward the complete role only on a positive gate; Revise failed capabilities; Narrow the Target or claim when evidence supports less; Stop the direction when trustworthy validation is not achievable.

## Evidence-Conditional Horizons

These horizons are not committed dates or delivery promises.

### Q2 - Complete First Role System

Entry requires a `V22` Continue decision. Run a conditional paid beta while expanding the validated slice toward the complete common role baseline, protected assessment pool, multiple unique checkpointed project and simulation Instances, evidence portfolio, and human-approved readiness reports. Stop expansion if assessment validity, authoring cost, or practitioner calibration does not scale.

### Q3 - Calibration and Governance

Entry requires credible complete-role evidence and repeatable authoring. Deepen blinded calibration, provenance and defense, role-market governance, and optional explicit Industry or Company Overlays backed by credible sources and reviewers. An adjacent role may be researched only if graph and Blueprint reuse is demonstrably high.

### Q4 - Repeatability and Partner Test

Entry requires evidence that the first role is not a bespoke services exercise. Test one adjacent role or a narrowly selected partner workflow with privacy-safe evidence sharing. If authoring remains bespoke, invest in governance and authoring tools instead of adding roles.

School, minor-facing, public credentialing, social, marketplace, and broad enterprise products remain Deferred and are not earned merely by completing these horizons.
