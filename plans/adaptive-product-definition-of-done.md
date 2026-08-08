# Adaptive Product Definition of Done

## Purpose

This file operationalizes `plans/product-completion-definition-of-done.md` for engineering execution. It does not replace the mission document and it cannot unlock external validation phases.

The product program is complete only when G01 through G09 are implemented, accepted on exact revisions, and the resulting production behavior satisfies the applicable D01-D12 contracts without creating stronger claims than the evidence supports.

## Non-negotiable invariants

1. G-series work is engineering enablement only. It never marks V00-V22 passed.
2. Self-report, chat quality, task completion, calibration score, confidence, or activity count never become mastery or readiness evidence.
3. Only trusted, provenance-bearing evaluator transitions may alter authoritative competency evidence.
4. The LLM may propose tutoring actions but may not mutate authoritative learner state directly.
5. Every learner-facing plan is bound to an exact Target and RoleProfile version.
6. Readiness is a deterministic projection against that exact profile and remains locked until its own DoD and validation boundary are satisfied.
7. Durable state, replay, ownership, deletion, recovery, and provider-failure behavior fail closed.
8. A phase is not `PASSED` because prose says so. It is `PASSED` only when machine state names reproducible evidence from an accepted exact revision.
9. No successor G phase starts from an unmerged stack. It starts from verified `main` after the prior phase is merged and, when behavior is deployed, production acceptance is complete.

## Phase state machine

`NOT_STARTED -> IMPLEMENTING -> VALIDATING -> PASSED`

Exceptional states are `BLOCKED_EXTERNAL` and `FAILED_RETRYABLE`. `PASSED` is terminal unless a regression invalidates its evidence; a regression reopens the earliest affected phase.

The machine companion is `plans/adaptive-product-state.json`. `scripts/product_gate.py` validates it in CI.

## Adaptive acceptance algorithm

For every change, derive the phase DoD from four inputs:

1. the active G phase and its mapped D01-D12 contracts;
2. the actual files/contracts touched by the exact revision;
3. the trust boundary crossed by the change;
4. failure consequences for learner claims, durable state, privacy, or production continuity.

The required test tiers are additive. A phase may add stronger gates but may never remove a mandatory tier for convenience.

### Risk tiers

- **Tier A — deterministic contract:** formatting, lint, strict typing, unit/branch coverage, schema validation, deterministic replay/idempotency where state changes.
- **Tier B — integration:** real persistence/migrations, cross-process/runtime smoke, frontend/backend contract tests, ownership boundaries, backward migration.
- **Tier C — adversarial:** tampering, duplicate/reordered events, stale versions, invalid evaluator, hint leakage, provider failure, disputed evidence, isolation/privacy failure.
- **Tier D — human simulation:** multi-step learner journeys that model realistic behavior rather than calling one function in isolation.
- **Tier E — deployed acceptance:** exact-SHA deployed create/resume/progress/evidence/delete/replay journeys whenever production behavior changes.

All product phases require A and D. State-bearing phases require B and C. Production-affecting phases require E before their post-merge acceptance record becomes `PASSED`.

## Human-simulation protocol

A human simulation is an executable trajectory with a named behavioral premise, multiple actions, and end-state assertions. Mock-only single-call tests do not satisfy this requirement.

Mandatory reusable personas are:

- **Overconfident learner:** maximizes self-rating/confidence and attempts to self-certify.
- **Assisted learner:** receives hints/guidance; assistance must remain provenance and must block independent promotion until a later clean observation.
- **Returning learner:** resumes durable state; replay must reproduce the same authoritative projection.
- **Disputed-evidence learner:** a trusted result is disputed or contradicted; the ledger stays auditable and deterministic.
- **Struggling learner:** repeated misconceptions and failed probes cause replanning rather than false progress.
- **Fast learner:** demonstrates evidence quickly; curriculum compresses without skipping required proof.
- **Provider-outage learner:** tutor/model dependency fails; authoritative state remains valid and recoverable.
- **Cross-account attacker:** attempts to read/change another learner's state; ownership/isolation fails closed.
- **Deletion learner:** requests deletion/export; privacy lifecycle reaches a verifiable terminal state.

Each phase selects the personas relevant to its trust boundary and records them in machine state.

## G-series minimum DoD

### G01 — Target and claim-integrity correction

Mapped contracts: D01, D02, D04, D11.

Done when Target dimensions are explicit/version-bound, RoleProfile terminology is separated from self-report, all legacy mastery/readiness shortcuts are removed or migrated, and UI/API copy cannot present planning signals as verified competence.

Human simulations: overconfident learner, returning legacy learner.

### G02 — Evidence and deterministic state contracts

Mapped contracts: D03, D05, D11.

Done when evidence records have deterministic IDs and provenance; authoritative competency state is separate from planning/diagnostic signals; trusted verdict transitions are deterministic/idempotent; invalid/mismatched evidence fails closed; misconceptions/review state are replayable; no public learner route can forge trusted evaluator writes; legacy states migrate without inventing evidence; readiness remains locked.

Human simulations: overconfident learner, assisted learner, returning learner, disputed-evidence learner.

### G03 — Deterministic curriculum planner

Mapped contracts: D02, D04, D06.

Done when the planner consumes exact Target/RoleProfile plus deterministic learner evidence state, emits an immutable learner-specific plan version, explains priority/delta reasons, produces bounded work unique to learner context, and deterministically replans after evidence/capacity/misconception changes without using unverified signals as mastery.

Human simulations: struggling learner, fast learner, assisted learner, returning learner.

### G04 — Tutor policy loop

Mapped contracts: D05, D07.

Done when tutoring loads authoritative state, scheduler/policy selects a bounded action, the model returns schema-validated proposals only, hint levels and assistance are ledgered, no answer leakage occurs before policy allows it, provider failure cannot corrupt progress, and policy decisions are observable/replayable.

Human simulations: struggling learner, assisted learner, fast learner, provider-outage learner.

### G05 — Trusted blueprint and unique-instance system

Mapped contracts: D08.

Done when versioned ItemFamily/Blueprint contracts are trusted inputs, generated instances are learner-bound and seed-reproducible, acceptance criteria/rubrics are stable, semantic duplication is bounded, and generation failure cannot silently weaken the assignment.

Human simulations: two learners on the same track, repeated regeneration, returning learner.

### G06 — Independent, retention, and transfer engine

Mapped contracts: D05, D09.

Done when independent verification, delayed retention probes, and transfer probes are distinct events; assistance withdrawal is enforced; 7-day and 30-day due-state semantics are deterministic; failures reopen gaps/replan; and neither immediate success nor schedule creation is misrepresented as retention proof.

Human simulations: assisted learner, fast learner, struggling learner, returning learner after delayed probes.

### G07 — Work provenance and simulations

Mapped contracts: D10.

Done when artifacts/checkpoints/modification/debugging/defense events retain learner/evaluator/tool provenance, simulation attempts are reproducible, artifact evidence is integrity-bound, and copied/unsupported work cannot become authoritative evidence without the required defense/verification path.

Human simulations: copied-artifact learner, modified-artifact learner, debugging learner, defense failure/recovery.

### G08 — Readiness projection

Mapped contracts: D11.

Done when readiness is a deterministic projection against one exact RoleProfile version, reports gaps/uncertainty/exclusions/overlay deltas, requires all evidence classes demanded by the profile, cannot be increased by self-report/chat/completion alone, and exposes the explicit human/external approval boundary before any stronger claim.

Human simulations: overconfident learner, incomplete-overlay learner, fully evidenced learner, disputed-evidence learner.

### G09 — Integration hardening

Mapped contracts: D03, D07, D12 plus all cross-cutting invariants.

Done when Postgres is authoritative, event/outbox/replay are consistent under concurrency, auth/ownership/isolation/export/deletion/redaction/recovery work end-to-end, provider failure is bounded, browser confidentiality holds, migrations/recovery are proven, and the deployed exact-SHA journey covers create/resume/progress/evidence/replan/tutor/delete/replay without state corruption or overclaiming.

Human simulations: returning learner, provider-outage learner, cross-account attacker, deletion learner, concurrency/retry learner.

## Per-phase evidence record

Every active phase in `plans/adaptive-product-state.json` records:

- mapped D01-D12 contracts;
- dependencies;
- status and exact branch;
- required risk tiers;
- implementation evidence paths;
- executable test evidence paths;
- human-simulation evidence paths/personas;
- exact accepted SHA when passed;
- production acceptance evidence when deployed behavior changed;
- explicit next phase.

The product gate rejects missing dependencies, branch/phase mismatch, phase skipping, invalid passed SHAs, missing human-simulation evidence, or a `PASSED` phase without the required evidence classes.
