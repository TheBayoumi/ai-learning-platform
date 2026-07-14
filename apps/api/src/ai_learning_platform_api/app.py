"""FastAPI application factory for the role-neutral F00 foundation."""

from fastapi import FastAPI

from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.health import create_health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application using validated local process settings only."""
    resolved_settings = settings if settings is not None else Settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(
        title="AI Career Learning Platform API",
        version="0.0.0",
        description="Role-neutral technical foundation endpoints only.",
    )
    app.include_router(create_health_router())
    return app
