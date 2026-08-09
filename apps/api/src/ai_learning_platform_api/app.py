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
from ai_learning_platform_api.learning.schemas import PlanView
from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository
from ai_learning_platform_api.persistence.schemas import AccountDataExportView
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.diagnostics import ApiHealthDiagnosticsMiddleware
from ai_learning_platform_api.transport.http.health import create_health_router
from ai_learning_platform_api.transport.http.learning import create_learning_router
from ai_learning_platform_api.transport.http.persistent_compatibility import (
    PersistentCompatibilityService,
    create_persistent_compatibility_router,
)
from ai_learning_platform_api.transport.http.privacy import create_privacy_router
from ai_learning_platform_api.transport.http.tutoring import create_tutoring_router
from ai_learning_platform_api.tutoring import (
    DisabledTutorGateway,
    TutorGateway,
    TutorService,
    VercelAiGateway,
)
from ai_learning_platform_api.tutoring.limits import TutorTurnLimiter


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
    compatibility_service: PersistentCompatibilityService | None = None
    tutor_service: TutorService | None = None
    tutor_limiter: TutorTurnLimiter | None = None
    secret = resolved_settings.learner_state_secret.get_secret_value()
    core_service = LearningPlanService(secret)

    if include_product_routes and resolved_settings.persistence_mode == "postgres":
        assert resolved_settings.database_url is not None
        database_runtime = DatabaseRuntime.create(resolved_settings.database_url.get_secret_value())
        postgres_repository = PostgresLearnerStateRepository(database_runtime.engine)
        persistent_service = PersistentLearningService(
            secret=secret,
            repository=postgres_repository,
            exposure_repository=postgres_repository,
            export_repository=postgres_repository,
            replay_repository=postgres_repository,
        )
        compatibility_service = PersistentCompatibilityService(
            secret=secret,
            persistent=persistent_service,
        )

    if include_product_routes:
        gateway_token = resolved_settings.tutor_gateway_token()
        gateway: TutorGateway
        if resolved_settings.tutor_mode == "vercel_ai_gateway":
            assert gateway_token is not None
            gateway = VercelAiGateway(
                token=gateway_token,
                model=resolved_settings.tutor_model,
                timeout_seconds=resolved_settings.tutor_timeout_seconds,
                max_output_tokens=resolved_settings.tutor_max_output_tokens,
            )
        else:
            gateway = DisabledTutorGateway()

        async def resolve_plan(account_id: str, state_token: str) -> PlanView:
            if compatibility_service is not None:
                return await compatibility_service.current_plan(
                    account_id=account_id,
                    state_token=state_token,
                )
            return core_service.resume(state_token)

        tutor_service = TutorService(
            gateway=gateway,
            resolve_plan=resolve_plan,
            session_secret=secret,
        )
        tutor_limiter = TutorTurnLimiter(
            max_concurrent_turns=resolved_settings.tutor_max_concurrent_turns,
            requests_per_window=resolved_settings.tutor_requests_per_window,
            window_seconds=resolved_settings.tutor_rate_window_seconds,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if tutor_service is not None:
                await tutor_service.aclose()
            if database_runtime is not None:
                await database_runtime.shutdown()
            runtime.shutdown()

    app = FastAPI(
        title="AI Career Learning Platform API",
        version="0.5.0" if include_product_routes else "0.0.0",
        description=(
            "Health, role diagnosis, personalized competency planning, durable learner state, "
            "bounded AI tutoring, anonymous data controls, and assessment calibration."
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
        if compatibility_service is None:
            app.include_router(create_learning_router(core_service))
        else:
            app.include_router(create_persistent_compatibility_router(compatibility_service))

        async def delete_current_account(account_id: str) -> bool:
            if persistent_service is None:
                return False
            return await persistent_service.delete_account(account_id=account_id)

        async def export_current_account(account_id: str) -> AccountDataExportView:
            if persistent_service is None:
                raise RuntimeError("persistent account export is unavailable")
            return await persistent_service.export_account(account_id=account_id)

        app.include_router(create_privacy_router(delete_current_account, export_current_account))
        assert tutor_service is not None
        assert tutor_limiter is not None
        app.include_router(create_tutoring_router(tutor_service, tutor_limiter))
    return app
