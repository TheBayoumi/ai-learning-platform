# Product Mission Constitution

## 1. Product Identity

**AI Career Learning Platform** is the working internal name, not the final commercial brand.

The product is a persistent one-to-one AI tutoring, mastery, and role-readiness engine for adult career acceleration. It combines conversational tutoring with deterministic learning, curriculum, evidence, and readiness services. It is not a chatbot, course library, static curriculum, quiz application, school replacement, credential issuer, or job-placement guarantee.

The following terms are constitutional and are reused throughout the product specifications:

- A **Target** resolves role, seniority, labor market, learner timeline, and applicable geography, stack, industry, and company requirements. Unknown optional overlays remain explicit; unresolved required dimensions block planning.
- A `RoleProfile` is a named, versioned outcome contract containing the common role baseline, required competencies, evidence requirements, exclusions, uncertainty, provenance, and review date. It is not a syllabus.
- A `CompetencyGraph` is the versioned outcome and prerequisite graph referenced by a `RoleProfile`.
- An **Overlay** is an explicit geography-, stack-, industry-, or company-specific delta kept separate from the common role baseline.
- A `CurriculumPolicyVersion` is the immutable set of deterministic planning rules.
- A `LearnerPlanVersion` is the immutable, learner-specific curriculum compiled from a `RoleProfile`, accepted evidence, learner constraints, active Overlays, a `CurriculumPolicyVersion`, and a stable pseudonymous learner-bound seed used only among pedagogically equivalent routes. Replanning creates a new version and a readable delta.
- A **Blueprint** is a versioned shared specification, verifier, assistance policy, and rubric for a task, project, or simulation. It must earn the trust level required for its use. An **Instance** is the unique, learner-bound task, project, or simulation served from a Blueprint.
- An `ItemFamily` is a versioned shared specification for practice or assessment items. An `ItemInstance` is its unique learner-bound surface form. Item and work trust paths are separate; both require per-Instance validation.
- **Structured evidence** is a provenance-bearing record of performance, assistance, evaluator or reviewer decisions, and every applicable policy, model, prompt, rubric, `ItemFamily`, `ItemInstance`, Blueprint, Instance, verifier, schema, and algorithm version.
- `ReadinessEvidence` is accepted structured evidence mapped to a required competency in a specific `RoleProfile`.
- **Verified mastery** requires independent no-hint performance, reasoning evidence, delayed retention, and transfer or near-transfer where applicable.
- `ReadinessState` is a deterministic, versioned conclusion derived from accepted `ReadinessEvidence` against one `RoleProfile`. It is never inferred from content completion.
- `partial_profile_evidence` means evidence for a validated competency slice. It is not complete-role readiness.

## 2. Problem Being Solved

Existing products separate capabilities that must operate as one control system. Conversational tutors adapt explanations but rarely maintain durable, auditable learner state. Adaptive platforms track mastery but provide limited dialogue and explanation adaptation. Career programs provide a destination but commonly use static paths, completion, or portfolio submission as proxies for readiness.

The product must know the bounded destination, diagnose the learner, continuously recompile the route, teach and reassess, verify performance after assistance is withdrawn, and connect defensible evidence to realistic work outcomes.

## 3. Primary Learner and Initial Market

The commercial product begins as an adult B2C career accelerator.

The **provisional, selection-gated first Target** is:

- **Role:** Junior Python Backend Engineer.
- **Seniority:** Entry-level or junior individual contributor.
- **Labor market:** Egypt and MENA-based learners targeting local or English-speaking remote roles.
- **Learner timeline:** 4-6 months for a learner who already has basic programming foundations. This is a planning assumption, not an outcome guarantee.
- **Learner segment:** Adults aged 18+ who know basic Python syntax and Git but lack production backend competence and defensible work evidence.
- **Stack Overlay:** Python, FastAPI, PostgreSQL, REST APIs, Git, automated testing, Docker, basic CI, debugging, documentation, and engineering communication.
- **Industry Overlay:** None.
- **Company Overlay:** None.

This Target advances only if the role-selection gate confirms current demand, a stable and bounded common baseline, at least two qualified practitioners, access to a real 20-50 learner recruitment channel, objective assessment of a meaningful competency slice, at least one realistic work simulation, and acceptable infrastructure and evaluation cost. The gate may narrow the labor market if local and remote expectations do not form a coherent baseline.

Failure replaces the Target before curriculum or assessment production begins. Its appearance in this constitution does not preserve it.

## 4. Core Value Proposition

For a resolved Target, the platform turns verified learner evidence into the next best learning and work action, then proves what remains when answer-level tutoring is withdrawn.

The `RoleProfile`, Blueprints, and shared rubrics preserve comparability. Each learner receives a different `LearnerPlanVersion` and unique task, project, and simulation Instances based on that learner's evidence, misconceptions, forgetting, pace, constraints, and active Overlays.

## 5. Product Control Loop

The product must complete and record this loop:

1. Resolve the Target.
2. Diagnose the learner using verified evidence rather than self-report alone.
3. Compile a learner-specific `LearnerPlanVersion`.
4. Teach, reassess, and replan when accepted evidence or declared constraints change.
5. Generate and validate unique learner-bound work Instances from approved Blueprints.
6. Collect structured evidence, including assistance and hint use.
7. Compute verified mastery and `ReadinessState` deterministically.
8. Expose remaining gaps, uncertainty, exclusions, and active or unresolved Overlays.

A feature that bypasses or obscures this loop is outside the product model.

## 6. Product Principles and Non-Negotiable Invariants

1. **Resolve before planning.** An underspecified Target does not produce a curriculum.
2. **The destination is shared; the route is not.** A `RoleProfile` defines outcomes. Each `LearnerPlanVersion` is recomputed from evidence and constraints.
3. **The LLM is a sensor and actuator.** It may converse, explain, evaluate, generate, and propose actions. It may not own or directly mutate mastery, curriculum, role requirements, evidence acceptance, or readiness.
4. **State is reproducible.** Mastery, planning, and readiness decisions are deterministic, versioned, auditable, and reproducible from structured evidence.
5. **Scaffold, then withdraw.** Performance that disappears without answer-level assistance is not learning evidence.
6. **Completion is not mastery or readiness.** Serious claims require independent performance, reasoning, retention, transfer, and realistic work evidence.
7. **Unique work, shared standards.** Learners targeting the same role do not receive identical curricula, tasks, projects, or simulations. Validated Blueprints and rubrics preserve equivalence.
8. **Provenance is mandatory.** Important artifacts require checkpoints, assistance disclosure, defense, modification requests, debugging, and unseen follow-up work.
9. **Overlays stay explicit.** Geography, stack, industry, and company deltas may not be hidden inside the common role baseline.
10. **Generated content earns trust.** Unvalidated generated items, projects, or simulations may not affect high-stakes mastery or readiness.
11. **Measure learning and role performance.** Time in product, message count, streaks, satisfaction, and raw completion are diagnostics, not success measures.
12. **Humans retain consequential judgment.** Contested grading, market validation, soft-skill judgment, accountability, and externally used first-year readiness reports require appropriate human involvement.
13. **Expansion is earned.** Evidence from one bounded adult technical role must justify broader roles, markets, or product shells.
14. **One engine, no hidden forks.** Future shells may change policy and presentation but may not create incompatible mastery, evidence, or readiness ownership.

## 7. Explicit Non-Goals

The product will not:

- become a generic chatbot, course catalogue, fixed syllabus, quiz bank, or content-completion product;
- guarantee employment, interviews, promotion, compensation, visas, or acceptance by every employer;
- claim that a simulation replaces workplace experience or consequential human judgment;
- replace mentorship, accountability, peer learning, social learning, emotional support, safeguarding, or institutional trust;
- serve minors or build school, employer, organization, marketplace, credentialing, social, or multi-role products during the initial validation;
- issue public credentials or automated external readiness certification;
- optimize addictive engagement mechanics or generated-content volume; or
- infer readiness from chat history, self-report, module completion, or an unreviewed portfolio.

## 8. First-Year Scope

The active first-year product is an adult career accelerator. Its initial relative 90-day validation is B2C only and tests one selection-gated technical role through a deeply validated 40-80-node competency slice and at least one realistic work outcome.

The 90-day period validates the platform. It does not promise that every learner becomes ready for the complete role within 90 days, and it is distinct from the 4-6 month learner preparation assumption. Expansion toward a complete role system occurs only after a positive evidence gate. Later first-year horizons are conditional, not delivery commitments.

Architecture may remain compatible with future organization, school, or child-facing shells. Those products are outside active first-year scope unless separately funded and approved with their own safety, privacy, pedagogy, and go-to-market program.

## 9. Definition of Learner Success

For an in-scope competency, learner success means the learner can:

- perform independently on tutor-silent work;
- explain the reasoning and relevant trade-offs;
- retain the capability after immediate, 7-day, and 30-day checks;
- transfer it to unseen work where applicable;
- complete, modify, debug, and defend a unique realistic work Instance;
- support the result with accepted, current structured evidence; and
- see remaining gaps, uncertainty, exclusions, and Overlay deltas.

During initial validation, success produces `partial_profile_evidence`, not a universal or complete-role "job ready" conclusion. Employment outcomes may follow, but they are not part of this definition.

## 10. Definition of Product Failure

The initial validation fails, requiring revision, narrowing, Target replacement, or termination, if the system cannot support the approved validation claim with stated uncertainty.

Failure includes any of the following:

- gains disappear when answer-level tutoring is removed or after delayed reassessment;
- identical inputs and versions do not reproduce the same deterministic state;
- system evidence does not meaningfully align with blinded practitioner-rated realistic work performance under the preregistered calibration method;
- unique work cannot remain valid, equivalent, and collision-resistant;
- consequential evidence lacks traceable provenance or disputed verdicts alter state;
- curricula become static or materially identical across learners;
- the role, learner channel, practitioner access, privacy, cost, latency, or evidence-integrity gates cannot be satisfied; or
- engagement, completion, or hiring outcomes are substituted for verified learning evidence.

A missed gate is reported explicitly. It is not converted into a weaker claim without review.

## 11. Claims the Company May Make

Only when supported by measured evidence and stated uncertainty, the company may claim that the platform:

- diagnoses gaps against a named and versioned `RoleProfile`;
- compiles and updates an evidence-driven learner-specific curriculum;
- verifies specified competencies through independent retention and transfer evidence;
- produces unique, provenance-bearing realistic work evidence;
- reports readiness or remaining gaps against the exact scope and exclusions of a `RoleProfile`; and
- reports commercial outcomes such as interviews or hiring as cohort-defined, confounded outcome signals rather than proof of learning causation.

For the initial validation, the allowed outcome claim is limited to:

> For a validated competency slice of the selected named role, the system can diagnose a learner's gaps, compile and update a learner-specific curriculum, teach what is missing, verify independent retention and transfer, generate a unique realistic work simulation, and produce evidence that meaningfully predicts practitioner-rated performance with stated uncertainty.

Any first-year readiness report used externally also requires a recorded human approval.

## 12. Claims the Company Must Not Make

The company must not claim:

- guaranteed employment, interviews, promotion, compensation, or employer acceptance;
- universal job readiness or readiness for every employer;
- complete-role readiness from the 90-day validation slice;
- that every eligible learner will be ready within 4-6 months;
- that completion, conversation fluency, self-report, or a polished artifact proves mastery;
- that hiring outcomes prove the learning system caused readiness;
- that an LLM, unvalidated generated assessment, or unreviewed portfolio is a sufficient judge;
- named legal compliance before review of actual markets, vendors, contracts, and data flows; or
- replacement of school, mentorship, accountability, social learning, safeguarding, credentialing institutions, or consequential human judgment.

## 13. Human-in-the-Loop Boundaries

Humans must:

- validate the `RoleProfile`, proof slice, Blueprints, rubrics, and realistic work outcome;
- review contested, conflicting, low-confidence, or consequential evaluator decisions;
- conduct blinded readiness-calibration review and preregister its metric, sample, uncertainty, and decision threshold;
- approve any first-year readiness report before it is used externally;
- own assessment validity, market interpretation, soft-skill judgment, accountability, and consequential decisions; and
- provide mentorship, coaching, escalation, and real-world context where needed.

Human decisions must themselves be recorded as structured evidence. A human review may resolve uncertainty; it may not silently overwrite history or conceal conflicting evidence.

## 14. Decision Rules for Future Features

A proposed feature is accepted only if every applicable answer is **yes**:

1. Does it operate on a resolved Target and preserve `RoleProfile` scope and explicit Overlays?
2. Does it preserve deterministic ownership of mastery, planning, evidence acceptance, and readiness?
3. Does it correctly compile or recompile a learner-specific `LearnerPlanVersion` rather than impose a static path?
4. Does served work remain unique, Blueprint-constrained, validated, and comparable?
5. Does it collect sufficient provenance and versions for audit and replay?
6. Does it increase valid independent performance, retention, transfer, or realistic work evidence rather than completion or engagement alone?
7. Does it prevent unvalidated, invalid, conflicting, low-confidence, or disputed evidence from changing learner state?
8. Does it preserve assistance withdrawal and expose dependency rather than hide it?
9. Does it keep consequential human responsibilities and external claim review intact?
10. Does it fit the approved adult validation scope, privacy boundary, operational capacity, and measured cost and latency limits?
11. Does it have an observable acceptance test and an evidence-based continue, revise, narrow, or stop gate?
12. Can every resulting claim name its `RoleProfile` version, evidence basis, exclusions, and uncertainty?

A failed or unanswered rule blocks the feature until it is revised or explicitly classified as deferred research.
