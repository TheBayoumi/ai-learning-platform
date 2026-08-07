"""FastAPI application factory for the deployed learning product slice."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_learning_platform_api.diagnostics import (
    DiagnosticEventSink,
    DiagnosticsRuntime,
    emit_diagnostic_event,
)
from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.diagnostics import ApiHealthDiagnosticsMiddleware
from ai_learning_platform_api.transport.http.health import create_health_router
from ai_learning_platform_api.transport.http.learning import create_learning_router
from ai_learning_platform_api.transport.http.persistent_compatibility import (
    PersistentCompatibilityService,
    create_persistent_compatibility_router,
)


def create_app(
    settings: Settings | None = None,
    *,
    diagnostics_runtime: DiagnosticsRuntime | None = None,
    diagnostic_event_sink: DiagnosticEventSink = emit_diagnostic_event,
    include_product_routes: bool = True,
) -> FastAPI:
    """Create the API using validated settings and explicit transport boundaries."""
    configure_logging("INFO")
    resolved_settings = settings if settings is not None else Settings()
    configure_logging(resolved_settings.log_level)
    runtime = (
        diagnostics_runtime if diagnostics_runtime is not None else DiagnosticsRuntime.create()
    )
    database_runtime: DatabaseRuntime | None = None
    persistent_service: PersistentLearningService | None = None
    secret = resolved_settings.learner_state_secret.get_secret_value()

    if include_product_routes and resolved_settings.persistence_mode == "postgres":
        assert resolved_settings.database_url is not None
        database_runtime = DatabaseRuntime.create(resolved_settings.database_url.get_secret_value())
        persistent_service = PersistentLearningService(
            secret=secret,
            repository=PostgresLearnerStateRepository(database_runtime.engine),
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if database_runtime is not None:
                await database_runtime.shutdown()
            runtime.shutdown()

    app = FastAPI(
        title="AI Career Learning Platform API",
        version="0.2.0" if include_product_routes else "0.0.0",
        description=(
            "Health, role diagnosis, personalized competency planning, durable learner state, "
            "and assessment calibration for the first career-learning slice."
            if include_product_routes
            else "Role-neutral technical foundation endpoints only."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        ApiHealthDiagnosticsMiddleware,
        runtime=runtime,
        event_sink=diagnostic_event_sink,
    )
    app.include_router(create_health_router())
    if include_product_routes:
        if persistent_service is None:
            app.include_router(create_learning_router(LearningPlanService(secret)))
        else:
            app.include_router(
                create_persistent_compatibility_router(
                    PersistentCompatibilityService(
                        secret=secret,
                        persistent=persistent_service,
                    )
                )
            )
    return app
