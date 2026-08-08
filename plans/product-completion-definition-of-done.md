# AI Career Learning Platform — Product Completion Definition of Done

## Purpose

This plan re-anchors implementation to the authoritative product strategy and mission after the initial technical foundation and publishable beta work.

The product is complete only when the learner-facing system closes the full career-learning control loop. A routed UI, durable plan storage, deployment, or a generic AI chat surface is not sufficient.

This document does not replace `specs/mission.md` or `specs/roadmap.md`. It translates them into an engineering completion program while preserving the formal validation boundary: V00/V01 and later practitioner/cohort evidence gates remain external and may not be fabricated or inferred from implementation.

## Product Goal

For one resolved career Target, the platform must:

1. resolve role, seniority, labor market, timeline, and explicit overlays;
2. diagnose the learner from evidence, using self-report only to prioritize diagnosis;
3. compile a versioned learner-specific curriculum from the role outcome graph, evidence, constraints, misconceptions, forgetting, and active overlays;
4. tutor with a policy-controlled Socratic loop in which the LLM proposes but does not own mastery, curriculum, evidence acceptance, or readiness;
5. withdraw assistance and verify independent reasoning, delayed retention, and transfer where applicable;
6. generate learner-bound tasks, projects, and work simulations from validated shared blueprints while preventing duplicate or near-duplicate served work;
7. capture artifact provenance, assistance, checkpoints, modification/debugging requests, and learner defense;
8. maintain replayable structured evidence and deterministic learner/mastery/readiness projections;
9. expose exact remaining gaps, uncertainty, exclusions, and overlay deltas against a named RoleProfile version; and
10. preserve privacy, deletion, recovery, isolation, auditability, and bounded provider failure behavior in production.

## Engineering Definition of Done

Engineering completion requires all of the following. A row may be implemented before its external evidence gate is satisfied, but the UI/API must label the claim state honestly.

### D01 — Resolved Target contract

- A Target contains role ID/version, seniority, labor market, learner timeline, geography, stack overlays, optional industry/company overlays, scope, exclusions, and unresolved overlay deltas.
- Planning is impossible for an unresolved required Target dimension.
- Target changes create a new plan version; prior evidence is preserved and remapped.
- Onboarding collects or explicitly accepts every required dimension.

### D02 — RoleProfile and competency graph

- RoleProfile is a versioned outcome contract, not a syllabus.
- Competencies have typed prerequisites/relationships and evidence requirements.
- Source/provenance, confidence, review state, effective date, and expiry are representable.
- The proof-role graph is persisted behind repository interfaces.

### D03 — Evidence ledger and replay

- Evidence-bearing changes append immutable events.
- Transactional outbox and idempotency prevent duplicate state changes.
- Learner projections can be rebuilt deterministically from the same events and versions.
- Conflicting/disputed evidence remains visible and cannot silently mutate authoritative state.

### D04 — Diagnostic gap map

- Self-report never grants mastery or readiness.
- Diagnostic results are versioned and mapped to competency evidence.
- Uncertainty remains explicit and can request stronger evidence.
- The gap map can be compared with self-report without conflating the two.

### D05 — Deterministic learner state

- Mastery, misconceptions, forgetting/review schedules, assessment state, and plan state have deterministic owners.
- Completion or confidence alone cannot increase verified mastery.
- Invalid, low-confidence, conflicting, or disputed evaluator output has no authoritative state effect.
- Mastery claims require independent no-hint evidence, reasoning, delayed retention, and transfer/near-transfer where applicable.

### D06 — Learner-specific curriculum planner

- LearnerPlanVersion is immutable and versioned.
- Replanning responds to accepted evidence, misconceptions, forgetting, failed performance, available time, Target/RoleProfile change, overlays, and policy version.
- Same learner-bound inputs and versions reproduce the same plan.
- Same-role learners receive non-identical served routes only among policy-equivalent choices; requirements and difficulty are never weakened.
- Every replan exposes a readable reasoned delta.

### D07 — Socratic tutor control loop

- The system loads authoritative learner state before a tutoring turn.
- A policy/scheduler selects the next skill/review and tutor move.
- The LLM emits schema-validated proposals/verdicts only.
- Hint use and assistance are recorded.
- Provider/model failure cannot accept evidence, change mastery, or corrupt the plan.
- The tutor returns control to the learner after assistance and schedules withdrawal/verification.

### D08 — Item/blueprint trust and unique instances

- ItemFamily and Blueprint trust states are explicit and separate.
- Every served ItemInstance/TaskInstance/ProjectInstance/WorkSimulationInstance is learner-bound, versioned, validated, and traceable to a seed and plan version.
- History/cohort exact and near-duplicate checks reject collisions.
- Generated untrusted content cannot affect high-stakes mastery/readiness.
- Shared rubrics preserve comparability while served instances remain unique.

### D09 — Independent, retention, and transfer verification

- Tutor-silent/no-hint checkpoints exist.
- Reasoning/explain-back evidence is first-class.
- Immediate, 7-day, and 30-day review/probe states are represented and scheduled.
- Transfer work is unseen and distinct from tutoring/practice exposure.
- Hinted success and delayed/no-hint success remain separately visible.

### D10 — Artifact provenance and work evidence

- Important work maintains immutable versions/checkpoints.
- Assistance disclosure is captured.
- Evidence acceptance can require hidden modification/debugging work and written/oral defense.
- Missing provenance or prohibited answer-level assistance blocks evidence acceptance.
- A polished artifact alone never grants mastery/readiness.

### D11 — Deterministic readiness state

- Readiness is derived from accepted evidence against one exact RoleProfile version.
- Mandatory gaps cannot be offset by unrelated strong evidence.
- Status exposes coverage, evidence quality, stale/disputed evidence, realistic-work status, uncertainty, exclusions, and active/unresolved overlays.
- No readiness percentage/status is inferred from self-report, chat fluency, activity completion, or unreviewed portfolio work.
- External first-year readiness reports remain human-approved only.

### D12 — Production and learner ownership

- PostgreSQL remains authoritative for durable learner state.
- Account ownership/authorization, environment isolation, export, deletion, retention, redaction, and recovery are enforced.
- Raw transcript retention remains bounded and separate from structured evidence.
- Browser assets contain no server secrets or confidential diagnostic data.
- Production deployment proves create/resume/progress/evidence/delete/replay-sensitive paths without weakening learning claims.

## Claim States

The product must distinguish these states in code and UI:

- `engineering_available`: capability exists and passes technical tests;
- `validation_locked`: capability exists but the required practitioner/item/cohort evidence gate has not passed;
- `partial_profile_evidence`: accepted evidence for an approved competency slice only;
- `ready_against_profile`: allowed only after the roadmap's evidence gates and required human approval pass.

No implementation milestone may silently promote itself from one state to another.

## Current Gap From Production Release e62a553f

The current production release provides a routed web workspace, durable PostgreSQL learner state, bounded tutoring transport, basic assessments, provisional adaptive activities, privacy/deletion, recovery, and deployment verification.

It does not yet satisfy the mission because:

- onboarding does not fully resolve Target seniority, labor market, timeline, and overlays;
- self-ratings are converted directly into a numeric field named mastery;
- learner-attested activity completion increases that mastery field;
- assessment and completion signals are blended into a public readiness percentage without the required trust, no-hint, retention, transfer, provenance, or realistic-work gates;
- competency graphs are catalog data rather than persisted versioned outcome/prerequisite graphs;
- there is no complete deterministic mastery/misconception/forgetting state machine;
- there is no validated Blueprint/ItemFamily trust pipeline or history-wide uniqueness index;
- there is no full artifact provenance, modification/debugging, and defense flow;
- there is no deterministic readiness projection meeting the mission contract.

## Implementation Order

1. **G01 — Target and claim-integrity correction**: implement fully resolved Target state; reclassify self-report/attested completion/uncalibrated assessment as planning signals only; remove false mastery/readiness presentation.
2. **G02 — Evidence/state contracts**: introduce versioned evidence, competency evidence state, misconception/review state, transition policy, and backward-compatible state migration.
3. **G03 — Deterministic curriculum planner**: immutable LearnerPlanVersion, explicit triggers, prerequisites, stable learner-bound tie breaking, readable deltas.
4. **G04 — Tutor policy loop**: structured evaluator verdicts, deterministic tutor-move state machine, hint ledger, bounded provider failure.
5. **G05 — Trusted item/blueprint and unique-instance system**: trust levels, validators, learner-bound seeds, collision checks, exposure records.
6. **G06 — Independent/retention/transfer engine**: no-hint checks, reasoning evidence, review scheduler, 7/30-day probes, unseen transfer.
7. **G07 — Work provenance and simulations**: artifact versions/checkpoints, assistance ledger, hidden modification/debugging, defense, realistic simulation instances.
8. **G08 — Readiness projection**: deterministic mandatory-gap/evidence-quality/uncertainty/overlay projection with validation locks and human-approval boundary.
9. **G09 — Product integration hardening**: end-to-end UI/API flows, export/delete/replay, privacy, latency/cost instrumentation, failure recovery, production verification.

The G-series is an engineering execution sequence only. It does not mark V00-V22 validation phases passed.

## Global Acceptance Gate

A G-slice is complete only when:

- the exact PR head passes API quality, Web quality, Runtime smoke, Phase gate, and Gate projection;
- tests prove the relevant mission invariants, not only happy paths;
- legacy durable state has an explicit compatibility/migration path;
- no browser or API surface overclaims mastery/readiness;
- production deployment succeeds after merge when the slice changes deployed behavior; and
- the next slice starts from the verified production `main`, not from an unmerged stack.
