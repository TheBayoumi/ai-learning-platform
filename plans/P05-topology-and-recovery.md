# P05 — Deployment topology and PostgreSQL recovery posture

## Status

`IMPLEMENTED_UNVERIFIED`

This increment prevents an avoidable cross-Atlantic database hop and makes database activation fail closed unless the restored schema passes a reusable recovery verifier.

## Selected topology

- Neon project region: `aws-us-west-2`
- Vercel backend function region: `pdx1`
- Vercel frontend dynamic-function region: `pdx1`
- Frontend static assets remain globally delivered through Vercel.

The original backend workflow targeted `fra1`, which would place durable API actions across the Atlantic from the existing Neon project. The project region cannot be changed in place, so the controlled beta aligns compute with the already-provisioned database. A future European data-residency migration requires a new Neon project and a separately verified data migration; it must not be presented as a configuration-only change.

## Recovery verifier

`scripts/verify_recovery.py` checks a database without disclosing connection details:

1. the exact expected Alembic revision;
2. all required public tables;
3. all required `ON DELETE CASCADE` relationships;
4. an optional rollback-only write drill that creates an account, learner state, event, and outbox record, deletes the account, verifies all dependent records disappear, and rolls the transaction back.

The deployment workflow runs this verifier immediately after Alembic and before changing application traffic when PostgreSQL mode is enabled.

## Rehearsal evidence — August 7, 2026

A temporary Neon branch was created from production database branch `main`:

- rehearsal branch name: `p05-restore-rehearsal-20260807`
- rehearsal branch ID: `br-raspy-sea-a6j6al0w`
- database: `neondb`
- expected revision: `20260724_01`

Verified on the isolated branch:

- the Alembic revision matched;
- all persistence tables were present;
- all four foreign-key deletion rules were `CASCADE`;
- an isolated account record could be written, read, deleted, and confirmed absent;
- the rehearsal branch was deleted after verification;
- the production database branch was not modified.

The branch ID is operational evidence only and contains no credential.

## Deployment transaction

1. Require exact accepted source on `main`.
2. Validate persistence and tutor modes.
3. Run Alembic against the server-only database URL.
4. Run the recovery verifier with the exact expected revision and rollback-only write check.
5. Set frontend and backend Vercel function region to `pdx1`.
6. Configure server-only runtime variables and secrets.
7. Deploy backend and frontend.
8. Verify the connected learner journey and publish the deployment status.

No application traffic should be switched to a restored database that fails any verifier check.

## Rollback and recovery sequence

### Application rollback

1. Set `AI_PLATFORM_PERSISTENCE_MODE=signed_state`.
2. Redeploy the last accepted source.
3. Confirm health, plan creation, and signed-state resume.
4. Keep PostgreSQL records intact for investigation and replay.

### Database recovery rehearsal

1. Create an isolated Neon branch from the selected recovery point.
2. Run `alembic upgrade head` on that branch.
3. Run `scripts/verify_recovery.py --expected-revision 20260724_01 --write-check` using a server-only branch connection URL.
4. Run the product integration suite against the branch.
5. Promote or migrate only after explicit approval and exact-source verification.
6. Delete failed or completed rehearsal branches.

## Resource and performance implications

- Aligning compute and database removes the prior intercontinental database round trip.
- Users outside western North America still incur geographic latency to dynamic functions; this is acceptable only for a bounded beta and must be measured from target markets.
- The recovery write drill uses one rolled-back transaction and four temporary records; it leaves no durable data.
- Neon branch rehearsals consume provider storage/compute while active and must be deleted after use.
- Per-process tutor limits do not replace provider spend caps or edge/WAF controls.

## Reproducibility

- Python runtime: 3.13.13
- `uv`: 0.11.18
- PostgreSQL CI image: 18-alpine
- Alembic revision: `20260724_01`
- Vercel region contract: `pdx1`
- Recovery and topology verifiers are committed and executed by CI/deployment.

## Claim boundary

This rehearsal proves that the current schema can be cloned and verified on an isolated provider branch. It does not establish a contractual recovery-time objective, recovery-point objective, multi-region failover, or compliance certification. Those claims require repeated timed drills and provider/account policies outside this source increment.
