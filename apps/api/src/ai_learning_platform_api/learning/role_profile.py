"""Deterministic RoleProfile graph metadata layered over the provisional role catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ai_learning_platform_api.learning.catalog import RoleDefinition

_DEFAULT_EVIDENCE_REQUIREMENTS: Final = (
    "trusted_evaluator",
    "independent",
    "no_assistance",
    "reasoning_verified",
)


@dataclass(frozen=True, slots=True)
class CompetencyProfile:
    """Role-specific dependency and evidence requirements for one competency."""

    competency_id: str
    prerequisites: tuple[str, ...]
    evidence_requirements: tuple[str, ...] = _DEFAULT_EVIDENCE_REQUIREMENTS


@dataclass(frozen=True, slots=True)
class RoleProfileGraph:
    """Version-bound deterministic graph used by curriculum planning."""

    role_id: str
    role_version: str
    graph_version: str
    evidence_policy_version: str
    competencies: dict[str, CompetencyProfile]


def _profiles(values: dict[str, tuple[str, ...]]) -> dict[str, CompetencyProfile]:
    return {
        competency_id: CompetencyProfile(
            competency_id=competency_id,
            prerequisites=prerequisites,
        )
        for competency_id, prerequisites in values.items()
    }


_GRAPHS: Final = {
    "junior-python-backend-engineer": _profiles(
        {
            "python": (),
            "rest": (),
            "postgresql": (),
            "git": (),
            "communication": (),
            "fastapi": ("python", "rest"),
            "testing": ("python",),
            "docker": ("fastapi",),
            "ci": ("testing", "git"),
            "debugging": ("python",),
        }
    ),
    "ai-application-engineer": _profiles(
        {
            "python": (),
            "git": (),
            "communication": (),
            "testing": ("python",),
            "fastapi": ("python",),
            "docker": ("fastapi",),
            "debugging": ("python",),
            "llm-applications": ("python", "testing"),
            "rag": ("llm-applications",),
            "ai-evaluation": ("llm-applications", "testing"),
        }
    ),
    "data-engineer": _profiles(
        {
            "python": (),
            "postgresql": (),
            "git": (),
            "communication": (),
            "testing": ("python",),
            "docker": ("python",),
            "ci": ("testing", "git"),
            "debugging": ("python",),
            "data-modeling": ("postgresql",),
            "data-pipelines": ("python", "postgresql"),
            "data-quality": ("data-pipelines", "testing"),
        }
    ),
}


def profile_for(role: RoleDefinition) -> RoleProfileGraph:
    """Return and validate the exact dependency graph for one catalog role version."""
    profiles = _GRAPHS.get(role.identifier)
    if profiles is None:
        raise ValueError(f"missing RoleProfile graph for {role.identifier}")
    role_ids = {item.identifier for item in role.competencies}
    if set(profiles) != role_ids:
        raise ValueError(
            f"RoleProfile graph does not match catalog competencies for {role.identifier}"
        )
    for profile in profiles.values():
        if profile.competency_id in profile.prerequisites:
            raise ValueError(f"self dependency in RoleProfile for {profile.competency_id}")
        if any(item not in role_ids for item in profile.prerequisites):
            raise ValueError(f"unknown prerequisite in RoleProfile for {profile.competency_id}")
    return RoleProfileGraph(
        role_id=role.identifier,
        role_version=role.version,
        graph_version=f"{role.version}.graph-v1",
        evidence_policy_version="competency-evidence-v1",
        competencies=profiles,
    )
