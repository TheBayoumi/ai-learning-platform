# Provider-Neutral Autonomous Executor Goal

## Purpose

Continue the approved autonomous development program regardless of whether the active executor is Codex, Claude Code, or another approved coding-agent runtime.

The executor is replaceable. Repository evidence is not.

## Authority order

Before acting, read and reconcile:

1. `AGENTS.md`
2. `specs/mission.md`
3. `specs/tech-stack.md`
4. `specs/roadmap.md`
5. `plans/autonomous-loop/state.json`
6. `plans/autonomous-loop/checkpoint.md`
7. `plans/autonomous-loop/run-log.md`
8. `plans/implementation-inventory.json`
9. the active phase ExecPlan
10. the active GitHub issue, pull request, current head SHA, review threads, and exact-head workflow results

Do not depend on private chat history from a previous executor.

## Start-of-run rules

- Confirm the repository, branch, exact HEAD, worktree status, and exclusive write ownership.
- Never run two write-capable executors in the same checkout.
- Treat an existing dirty worktree as potential handoff state. Inspect it before changing it.
- Preserve valid work regardless of which executor produced it.
- Do not reset, discard, stash, overwrite, or recreate existing work without repository evidence that it is invalid or unrelated.
- Continue from the smallest exact unfinished action recorded by the repository.
- Quota exhaustion is `QUOTA_PAUSED`, not phase failure.

## Phase selection

- Recompute the validation and foundation lanes from repository state.
- Select only the earliest eligible bounded phase or repair.
- A validation phase blocked by unfakeable external evidence does not block an independently eligible role-neutral foundation phase.
- Do not unlock later validation phases or product capabilities without their recorded prerequisites.
- Do not begin a second phase in the same invocation.

When the next phase is not formally defined, create or update one self-contained ExecPlan with entry conditions, outputs, non-goals, tests, rollback, resource effects, and gate rules. Do not create a speculative multi-phase implementation plan.

## Execution model

- Use one writer.
- Use bounded read-only architecture, roadmap, security, deployment, or verification reviewers only when they materially reduce risk.
- Verify agent findings against repository evidence; agreement is not proof.
- Implement the smallest coherent slice authorized by the active phase.
- Do not change product scope, validation claims, deployment topology, dependencies, or constitutional policy merely because a different executor prefers another approach.

## Verification and publication

For every internally decidable technical phase:

1. complete implementation, adversarial tests, local gates, and independent read-only verification;
2. publish one bounded implementation revision;
3. require that exact SHA to pass every check named by `plans/autonomous-loop/controller-policy.json`;
4. reject pending, failed, cancelled, skipped, renamed, stale, merge-ref, or previous-SHA evidence;
5. repair confirmed failures within the same phase without asking for phase acceptance;
6. after the implementation SHA passes, publish a separate acceptance-state revision recording immutable evidence;
7. require the acceptance-state revision's own exact-head checks to pass; and
8. record the accepted revisions and workflow evidence durably before stopping at the phase boundary.

GitHub Actions is the exact-revision acceptance authority for machine-verifiable technical gates. It does not replace independent review or phase-specific evidence.

## Human and external blockers

Use `WAITING_EXTERNAL` for evidence that cannot be created by the executor, including observed demand, practitioner participation, recruitment-channel proof, legal approval, pilot outcomes, and measured external cost.

Use `WAITING_HUMAN` only when a consequential and potentially irreversible choice has no approved policy, repository evidence, or safe reversible default.

Do not use `WAITING_HUMAN` for ordinary technical choices, phase acceptance, commits, pushes, CI repair, documentation acceptance, reversible configuration, or lack of chat confirmation.

## Provider portability

A change of executor must not change:

- the active phase;
- scope or non-goals;
- acceptance criteria;
- required GitHub checks;
- state vocabulary;
- external blocker classification;
- one-writer policy; or
- phase-boundary discipline.

Provider-specific agents or tools may optimize execution only. When a named custom agent is unavailable, use a bounded read-only reviewer with the same responsibility.

## End-of-run record

Before stopping, update the applicable ExecPlan, state, checkpoint, run log, and implementation inventory. Record:

- executor runtime;
- active phase and gate;
- exact starting and published SHAs;
- changes made;
- validation actually executed;
- independent review findings and resolutions;
- exact GitHub run and job evidence;
- blockers and residual risks; and
- one next eligible action.

Stop before implementing that next action.
