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
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.diagnostics import ApiHealthDiagnosticsMiddleware
from ai_learning_platform_api.transport.http.health import create_health_router
from ai_learning_platform_api.transport.http.learning import create_learning_router


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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            runtime.shutdown()

    app = FastAPI(
        title="AI Career Learning Platform API",
        version="0.1.0" if include_product_routes else "0.0.0",
        description=(
            "Health, role diagnosis, personalized competency planning, and signed progress "
            "state for the first deployed career-learning slice."
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
        service = LearningPlanService(
            resolved_settings.learner_state_secret.get_secret_value()
        )
        app.include_router(create_learning_router(service))
    return app
