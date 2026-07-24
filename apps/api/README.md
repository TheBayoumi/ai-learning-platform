# AI Learning Platform API

This FastAPI service exposes the first career-learning vertical slice: a provisional
Junior Python Backend Engineer role profile, competency self-diagnosis,
learner-unique practical missions, evidence cycles, adaptive replanning, and
assessment calibration.

## Product routes

- `GET /api/v1/roles`
- `POST /api/v1/plans`
- `POST /api/v1/plans/resume`
- `POST /api/v1/plans/replan`
- `POST /api/v1/progress`
- `POST /api/v1/assessments/start`
- `POST /api/v1/assessments/submit`
- `GET /health/live`
- `GET /health/ready`

The product route contract is identical in both persistence modes.

## Persistence modes

`AI_PLATFORM_PERSISTENCE_MODE` accepts:

- `signed_state` — the current rollback-compatible default. The browser-carried,
  HMAC-protected token is authoritative and PostgreSQL is not initialized.
- `postgres` — PostgreSQL is authoritative. The existing signed token remains a
  bounded browser projection and migration envelope, but every accepted mutation
  verifies the stored aggregate version and atomically writes the snapshot,
  append-only event, idempotency record, and transactional outbox record.

`postgres` mode requires:

```text
AI_PLATFORM_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<database>
AI_PLATFORM_PERSISTENCE_MODE=postgres
AI_PLATFORM_LEARNER_STATE_SECRET=<at-least-32-UTF-8-bytes>
```

The database URL is a server-only secret. Only the `postgresql+psycopg://` driver
boundary is accepted. Application startup creates a lazy async SQLAlchemy engine;
it does not run migrations automatically.

The Next.js same-origin proxy assigns a provider-neutral anonymous account identifier
in an `HttpOnly`, `SameSite=Lax` cookie and forwards it only to the FastAPI server.
When PostgreSQL mode first receives a valid legacy signed token, the API imports that
state into the owned aggregate. Modified tokens fail closed.

This anonymous account boundary provides durable same-browser continuation and a
migration path to managed OIDC. It is not cross-device identity or production login.

## Database migrations

From `apps/api` with `AI_PLATFORM_DATABASE_URL` configured:

```powershell
uv sync --locked --all-groups
uv run --locked alembic upgrade head
uv run --locked alembic current
```

The CI migration gate verifies:

```powershell
uv run --locked alembic upgrade head
uv run --locked alembic downgrade base
uv run --locked alembic upgrade head
```

Do not switch production to `postgres` before the exact application revision and the
migration revision both pass API quality, PostgreSQL integration, web quality,
runtime smoke, phase gate, and gate projection.

Rollback is configuration-first: switch back to `signed_state` without deleting the
PostgreSQL records. The initial migration is reversible, but production downgrade is
not part of normal rollback because it would remove durable records.

## Local development

Signed-state mode:

```powershell
uv sync --locked --all-groups
$env:AI_PLATFORM_LEARNER_STATE_SECRET = "local-secret-with-at-least-thirty-two-bytes"
uv run uvicorn ai_learning_platform_api.main:app --reload
```

PostgreSQL mode:

```powershell
$env:AI_PLATFORM_DATABASE_URL = "postgresql+psycopg://localhost/ai_learning_platform"
$env:AI_PLATFORM_PERSISTENCE_MODE = "postgres"
$env:AI_PLATFORM_LEARNER_STATE_SECRET = "local-secret-with-at-least-thirty-two-bytes"
uv run --locked alembic upgrade head
uv run uvicorn ai_learning_platform_api.main:app --reload
```

The health-only compatibility artifact remains generated independently:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi write openapi/health.openapi.json
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi check openapi/health.openapi.json
```

## Verification

```powershell
uv run ruff format --check . ../../scripts
uv run ruff check . ../../scripts
uv run mypy src tests ../../scripts
uv run alembic upgrade head
uv run coverage run -m pytest
uv run coverage report --fail-under=95
```

The PostgreSQL integration tests require `AI_PLATFORM_DATABASE_URL`; they are skipped
only when no database fixture is configured. CI always supplies an ephemeral
PostgreSQL service.

## Claim boundary

Durable storage does not validate the provisional role, turn learner attestations
into externally verified evidence, select an OIDC provider, add organization tenancy,
or prove mastery or job readiness.
