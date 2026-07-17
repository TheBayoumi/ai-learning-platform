"""FastAPI application factory for the role-neutral technical foundation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_learning_platform_api.diagnostics import (
    DiagnosticEventSink,
    DiagnosticsRuntime,
    emit_diagnostic_event,
)
from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.diagnostics import ApiHealthDiagnosticsMiddleware
from ai_learning_platform_api.transport.http.health import create_health_router


def create_app(
    settings: Settings | None = None,
    *,
    diagnostics_runtime: DiagnosticsRuntime | None = None,
    diagnostic_event_sink: DiagnosticEventSink = emit_diagnostic_event,
) -> FastAPI:
    """Create an application using validated local process settings only."""
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
        version="0.0.0",
        description="Role-neutral technical foundation endpoints only.",
        lifespan=lifespan,
    )
    app.add_middleware(
        ApiHealthDiagnosticsMiddleware,
        runtime=runtime,
        event_sink=diagnostic_event_sink,
    )
    app.include_router(create_health_router())
    return app
