# API Foundation

This FastAPI project is the role-neutral F00 transport foundation. It contains
only process configuration, structured logging, and configuration-only health
checks; it has no database, external service, learner, or learning-state logic.

The canonical health-only OpenAPI artifact is generated from the application
factory rather than maintained as a parallel schema. Run these commands from
this directory:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi write openapi/health.openapi.json
uv run --locked python -m ai_learning_platform_api.contracts.health_openapi check openapi/health.openapi.json
```

The first command is an intentional update. The second is the non-mutating drift
gate used by CI.

The F01-02 TypeScript health validator is also generated from the verified
artifact with no schema library or handwritten consumer DTO:

```powershell
uv run --locked python -m ai_learning_platform_api.contracts.health_typescript write openapi/health.openapi.json ../web/server/contracts/generated/health-response.ts
uv run --locked python -m ai_learning_platform_api.contracts.health_typescript check openapi/health.openapi.json ../web/server/contracts/generated/health-response.ts
```

Check mode never changes the generated file. Unsupported contract semantics fail
before write mode can touch its target.
