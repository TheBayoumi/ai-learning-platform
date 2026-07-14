"""Configuration-only health transport."""

from fastapi import APIRouter

from ai_learning_platform_api.transport.http.schemas import HealthResponse


def create_health_router() -> APIRouter:
    """Build health routes without attaching product or infrastructure state."""
    router = APIRouter(tags=["health"])

    @router.get("/health/live", response_model=HealthResponse, operation_id="health_live")
    async def live() -> HealthResponse:
        """Report that the in-process API can respond."""
        return HealthResponse(status="ok", detail="process is live")

    @router.get("/health/ready", response_model=HealthResponse, operation_id="health_ready")
    async def ready() -> HealthResponse:
        """Report only that local configuration and the factory are valid."""
        return HealthResponse(
            status="ok",
            detail="configuration is valid; no external dependency checks are performed",
        )

    return router
