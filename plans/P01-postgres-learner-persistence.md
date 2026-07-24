# P01 — PostgreSQL Learner Persistence Foundation

## Goal

Replace browser-carried signed learner state as the only system of record with a
PostgreSQL-backed, provider-neutral persistence boundary while preserving the
existing deterministic learning engine and deployed learner workflow.

## Current problem

The deployed product can create, assess, replan, progress, and resume a learner,
but the authoritative state is an HMAC-signed token stored in one browser. This
prevents cross-device continuation, account ownership, safe concurrency, durable
audit history, replay, deletion workflows, and reliable background processing.

## Delivery sequence

### P01-01 — Configuration and contracts

- Add an explicit persistence mode: `signed_state` or `postgres`.
- Keep `signed_state` as the default until the PostgreSQL path passes every gate.
- Require a secret PostgreSQL URL when `postgres` is selected.
- Accept only the explicit `postgresql+psycopg://` driver boundary.
- Ensure configuration values cannot appear in logs, errors, browser assets, or
  generated client contracts.
- Define persistence repository and unit-of-work contracts without moving
  deterministic planning logic into infrastructure code.

### P01-02 — Tooling and migrations

Provisional implementation choice:

- SQLAlchemy `2.0.51` rather than the SQLAlchemy 2.1 prerelease line;
- Alembic `1.18.5`;
- Psycopg `3.3.4` with Python 3.13 support.

The dependency change must update the locked dependency graph reproducibly and
record installation size, startup impact, connection-pool behavior, failure
behavior, and replacement boundaries.

Initial migrations create:

- provider-neutral account identities;
- learner aggregate ownership and current state snapshots;
- append-only learner-domain events;
- idempotency records for evidence-bearing commands; and
- transactional outbox records.

Directly identifying account data must remain separable from append-only payloads.

### P01-03 — Repository integration

- Persist canonical `LearnerState` JSON with an explicit schema version.
- Use optimistic concurrency through an aggregate version.
- Require idempotency keys for evidence-bearing state transitions.
- Write the snapshot, append-only event, idempotency record, and outbox record in
  one transaction.
- Keep the existing `LearningPlanService` deterministic and persistence-independent.
- Reject stale aggregate versions and conflicting idempotency-key reuse.
- Never return an empty or newly generated learner state when storage fails.

### P01-04 — API and migration path

- Introduce explicit account context without selecting an OIDC vendor.
- Add authenticated create, resume, assessment, evidence, and replan orchestration
  around the existing deterministic service.
- Support a one-time import of a valid signed-state token into an owned database
  aggregate.
- Reject modified, oversized, stale, or role-incompatible legacy tokens.
- Do not silently trust browser identity or allow account identifiers in request
  bodies to determine ownership.

### P01-05 — Full-stack learner continuation

- Replace browser-local state-token ownership with an opaque server session/account
  projection.
- Preserve the current onboarding and dashboard behavior.
- Add explicit loading, conflict, unavailable, expired-session, and migration
  failure states.
- Prevent duplicate submissions during retry or reconnect.
- Confirm browser bundles contain no database URL, provider subject, learner event,
  or server-only configuration.

## Testing strategy

- Unit tests for configuration, repository contracts, canonical serialization,
  optimistic concurrency, and idempotency conflict rules.
- Migration tests from an empty PostgreSQL database and downgrade/upgrade round
  trips.
- PostgreSQL integration tests for transaction rollback, duplicate delivery,
  concurrent writers, and outbox atomicity.
- API tests for ownership, stale versions, duplicate commands, unavailable
  database behavior, and signed-state migration.
- Web tests for retries, conflicts, migration, and unavailable states.
- API line and branch coverage remains at least 95%.
- Existing web quality, production build, runtime smoke, phase gate, and gate
  projection remain green.

## Performance and resource boundaries

- No database connection is created in `signed_state` mode.
- Connection pools are bounded and explicitly disposed during shutdown.
- Request handlers must not perform blocking database work on the event loop.
- P95 persistence latency and transaction duration are measured with a fixed local
  PostgreSQL fixture before enabling the mode in deployment.
- Event, snapshot, idempotency, and outbox payload sizes are bounded.

## Rollout and rollback

1. Merge configuration and contracts with `signed_state` still active.
2. Add PostgreSQL dependencies, migrations, and repositories behind `postgres` mode.
3. Deploy with the database configured but the mode still disabled.
4. Run migration, transaction, confidentiality, and end-to-end verification.
5. Enable `postgres` only after exact-head checks pass.
6. Roll back by returning to `signed_state` mode before any destructive migration;
   database records remain intact for diagnosis and replay.

No migration may delete or rewrite legacy learner evidence during rollout.

## Non-goals

- Selecting a managed OIDC vendor.
- Production login or social-login UI.
- Organization tenancy or employer/admin dashboards.
- Object storage, LLM tutoring, payment, notifications, or readiness claims.
- Treating the provisional target role or calibration bank as market validated.

## Claim boundary

P01 establishes product persistence infrastructure only. It does not satisfy V00,
unlock V01, validate the target role, certify mastery, or prove job readiness.
