"""Deterministic Target resolution for career-plan creation and migration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.schemas import TargetRequest, TargetView


@dataclass(frozen=True, slots=True)
class TargetDefaults:
    """Provisional resolved Target defaults used for explicit onboarding and legacy migration."""

    seniority: str
    labor_market: str
    timeline_weeks: int
    geography: str
    stack_overlays: tuple[str, ...]
    scope: str
    exclusions: tuple[str, ...]


_PYTHON_BACKEND: Final = TargetDefaults(
    seniority="Entry-level / junior individual contributor",
    labor_market="Egypt and MENA local roles or English-speaking remote roles",
    timeline_weeks=20,
    geography="Egypt / MENA",
    stack_overlays=(
        "Python",
        "FastAPI",
        "PostgreSQL",
        "REST APIs",
        "Git",
        "Automated testing",
        "Docker",
        "Basic CI",
        "Debugging",
        "Documentation",
        "Engineering communication",
    ),
    scope=(
        "Provisional adult B2C preparation for a bounded Junior Python Backend Engineer "
        "role profile."
    ),
    exclusions=(
        "No employment, interview, compensation, or employer-acceptance guarantee.",
        "No company- or industry-specific requirement is assumed unless supplied as an overlay.",
        "Role validation remains locked until the external V00/V01 evidence gates pass.",
    ),
)

_AI_APPLICATION: Final = TargetDefaults(
    seniority="Entry-level / junior individual contributor",
    labor_market="Egypt and MENA local roles or English-speaking remote roles",
    timeline_weeks=24,
    geography="Egypt / MENA",
    stack_overlays=(
        "Python",
        "FastAPI",
        "LLM application engineering",
        "Retrieval-augmented generation",
        "AI evaluation and safety",
        "Automated testing",
        "Docker",
        "Debugging and observability",
        "Engineering communication",
    ),
    scope="Provisional engineering-only AI Application Engineer Target candidate.",
    exclusions=(
        "This candidate has not passed the initial role-selection validation gate.",
        "No model-training, research-scientist, company-specific, or hiring-readiness claim is implied.",
    ),
)

_DATA_ENGINEER: Final = TargetDefaults(
    seniority="Entry-level / junior individual contributor",
    labor_market="Egypt and MENA local roles or English-speaking remote roles",
    timeline_weeks=24,
    geography="Egypt / MENA",
    stack_overlays=(
        "Python",
        "PostgreSQL",
        "Analytical data modeling",
        "Data pipelines and orchestration",
        "Data quality and lineage",
        "Automated testing",
        "Docker",
        "Basic CI",
        "Debugging and observability",
        "Engineering communication",
    ),
    scope="Provisional engineering-only Data Engineer Target candidate.",
    exclusions=(
        "This candidate has not passed the initial role-selection validation gate.",
        "No company-, cloud-vendor-, industry-, or hiring-readiness requirement is assumed.",
    ),
)

_DEFAULTS: Final = {
    "junior-python-backend-engineer": _PYTHON_BACKEND,
    "ai-application-engineer": _AI_APPLICATION,
    "data-engineer": _DATA_ENGINEER,
}


def default_target_for(role: RoleDefinition) -> TargetView:
    """Return one explicit, fully resolved provisional Target for a catalog role."""
    defaults = _DEFAULTS[role.identifier]
    return _view(role=role, request=None, defaults=defaults)


def resolve_target(role: RoleDefinition, request: TargetRequest | None) -> TargetView:
    """Resolve an explicit Target, falling back only for legacy API compatibility."""
    defaults = _DEFAULTS[role.identifier]
    return _view(role=role, request=request, defaults=defaults)


def _view(
    *,
    role: RoleDefinition,
    request: TargetRequest | None,
    defaults: TargetDefaults,
) -> TargetView:
    if request is None:
        seniority = defaults.seniority
        labor_market = defaults.labor_market
        timeline_weeks = defaults.timeline_weeks
        geography = defaults.geography
        stack_overlays = list(defaults.stack_overlays)
        industry_overlay = None
        company_overlay = None
    else:
        seniority = request.seniority.strip()
        labor_market = request.labor_market.strip()
        timeline_weeks = request.timeline_weeks
        geography = request.geography.strip()
        stack_overlays = [item.strip() for item in request.stack_overlays]
        industry_overlay = _optional(request.industry_overlay)
        company_overlay = _optional(request.company_overlay)

    return TargetView(
        role_id=role.identifier,
        role_version=role.version,
        seniority=seniority,
        labor_market=labor_market,
        timeline_weeks=timeline_weeks,
        geography=geography,
        stack_overlays=stack_overlays,
        industry_overlay=industry_overlay,
        company_overlay=company_overlay,
        validation_state="provisional",
        scope=defaults.scope,
        exclusions=list(defaults.exclusions),
    )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
