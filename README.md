# Codex agent package for the AI Career Learning Platform

Copy the contents of this directory into the repository root:

```text
AGENTS.md
.codex/
  config.toml
  agents/
    architecture-guardian.toml
    learning-evidence-reviewer.toml
    mission-guardian.toml
    phase-worker.toml
    roadmap-gate-reviewer.toml
    verification-reviewer.toml
```

The custom agents intentionally omit `model` and `model_reasoning_effort`, so they inherit the model and intelligence/reasoning level selected by the parent Codex session.

Suggested first command:

```text
Review the current repository against AGENTS.md and the three specs. Delegate mission, learning-evidence, architecture, and roadmap reviews in parallel. Continue your own repository inspection while they run, wait for all completed reviews before finalizing, then return one prioritized implementation recommendation. Do not modify files.
```

Suggested phase implementation command:

```text
Implement roadmap phase <PHASE_ID>. First delegate read-only exploration and the relevant constitutional reviews. Create or update a self-contained ExecPlan, then use only one phase_worker for edits. Run verification_reviewer after implementation, reconcile confirmed findings, execute all affected checks, and report the gate disposition. Do not begin the next phase.
```
