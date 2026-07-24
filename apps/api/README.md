# AI Learning Platform API

This FastAPI service now exposes the first deployed career-learning vertical slice.
It retains the narrow health contract and adds a provisional Junior Python Backend
Engineer role profile, competency self-diagnosis, learner-unique practical missions,
signed resumable learner state, and progress updates.

## Product routes

- `GET /api/v1/roles`
- `POST /api/v1/plans`
- `POST /api/v1/plans/resume`
- `POST /api/v1/progress`
- `GET /health/live`
- `GET /health/ready`

The first slice is intentionally stateless on the server. The API signs the complete
learner state with `AI_PLATFORM_LEARNER_STATE_SECRET`; the browser stores the signed
token and returns it when resuming or completing an activity. Tampered state is
rejected. Production must configure a unique secret of at least 32 UTF-8 bytes.

This does not yet provide accounts, cross-device persistence, tenancy, a database,
payments, or LLM tutoring. Those capabilities require separately provisioned
services and credentials and must not be inferred from this slice.

## Local development

```powershell
uv sync --locked --all-groups
$env:AI_PLATFORM_LEARNER_STATE_SECRET = "local-secret-with-at-least-thirty-two-bytes"
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
uv run coverage run -m pytest
uv run coverage report --fail-under=95
```
