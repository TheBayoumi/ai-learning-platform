"""Versioned provisional role profile used by the first product slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ActivityTemplate:
    """A bounded activity template for one competency."""

    title: str
    objective: str
    deliverable: str
    acceptance_criteria: tuple[str, ...]
    estimated_minutes: int


@dataclass(frozen=True, slots=True)
class CompetencyDefinition:
    """A weighted competency in a role profile."""

    identifier: str
    name: str
    category: str
    description: str
    weight: int
    activities: tuple[ActivityTemplate, ...]


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    """A versioned role profile."""

    identifier: str
    version: str
    title: str
    summary: str
    competencies: tuple[CompetencyDefinition, ...]


def _activity(
    title: str,
    objective: str,
    deliverable: str,
    *criteria: str,
    minutes: int = 90,
) -> ActivityTemplate:
    return ActivityTemplate(
        title=title,
        objective=objective,
        deliverable=deliverable,
        acceptance_criteria=criteria,
        estimated_minutes=minutes,
    )


PYTHON_BACKEND_ROLE: Final = RoleDefinition(
    identifier="junior-python-backend-engineer",
    version="2026.07-provisional-1",
    title="Junior Python Backend Engineer",
    summary=(
        "A provisional Egypt/MENA-oriented role profile for learners targeting local or "
        "English-speaking remote Python backend positions."
    ),
    competencies=(
        CompetencyDefinition(
            "python",
            "Python engineering",
            "language",
            "Write maintainable typed Python with clear boundaries and error handling.",
            14,
            (
                _activity(
                    "Build a typed service module",
                    "Turn a small business rule into a typed, testable Python service.",
                    "A Python module plus focused unit tests and a short design note.",
                    "Public functions are typed",
                    "Invalid input fails explicitly",
                    "Tests cover success and failure paths",
                ),
                _activity(
                    "Refactor a brittle Python workflow",
                    "Separate parsing, validation, and domain decisions without changing behavior.",
                    "A refactored module, regression tests, and before/after rationale.",
                    "Behavior is preserved",
                    "Responsibilities are separated",
                    "No broad exception swallowing remains",
                ),
            ),
        ),
        CompetencyDefinition(
            "fastapi",
            "FastAPI service design",
            "backend",
            "Design validated HTTP APIs with explicit contracts and dependency boundaries.",
            13,
            (
                _activity(
                    "Implement a production-shaped FastAPI endpoint",
                    "Create one resource workflow with validation and deterministic errors.",
                    "Endpoint code, request/response models, and API tests.",
                    "OpenAPI reflects the contract",
                    "Invalid requests have stable responses",
                    "The route delegates domain logic",
                ),
                _activity(
                    "Add an API adapter boundary",
                    "Keep transport concerns separate from business decisions.",
                    "A router, service interface, adapter implementation, and tests.",
                    "Transport types do not leak into the domain",
                    "The adapter is replaceable in tests",
                    "Timeout and failure behavior are bounded",
                ),
            ),
        ),
        CompetencyDefinition(
            "postgresql",
            "PostgreSQL data modeling",
            "data",
            "Model relational data, constraints, indexes, and transactional changes.",
            12,
            (
                _activity(
                    "Design a transactional schema",
                    "Model a learner-like workflow with integrity enforced by the database.",
                    "DDL, an ER explanation, representative queries, and rollback notes.",
                    "Primary and foreign keys are explicit",
                    "Constraints encode invariants",
                    "Indexes follow query patterns",
                ),
                _activity(
                    "Diagnose a slow relational query",
                    "Use query shape and indexing evidence to propose a bounded optimization.",
                    "Query, explain-plan interpretation, index change, and validation notes.",
                    "The bottleneck is evidenced",
                    "The proposed index is selective",
                    "Write-cost trade-offs are explained",
                ),
            ),
        ),
        CompetencyDefinition(
            "rest",
            "REST API contracts",
            "backend",
            "Choose resources, methods, status codes, pagination, and idempotency deliberately.",
            10,
            (
                _activity(
                    "Design a resource API contract",
                    "Specify a small workflow before implementation.",
                    "An OpenAPI fragment with examples and error semantics.",
                    "Resource names are stable",
                    "Status codes match outcomes",
                    "Retry and idempotency behavior are stated",
                ),
                _activity(
                    "Review an inconsistent API",
                    "Identify contract drift and propose a compatible correction path.",
                    "A review report and versioned migration proposal.",
                    "Breaking changes are identified",
                    "Compatibility is preserved where possible",
                    "Errors use one documented shape",
                ),
            ),
        ),
        CompetencyDefinition(
            "testing",
            "Automated testing",
            "quality",
            "Create focused unit, integration, and contract tests that prove behavior.",
            12,
            (
                _activity(
                    "Build a layered test strategy",
                    "Cover one service workflow without overusing end-to-end tests.",
                    "Unit, API integration, and contract tests with a coverage rationale.",
                    "Tests fail for meaningful regressions",
                    "External boundaries are controlled",
                    "Assertions describe observable behavior",
                ),
                _activity(
                    "Repair a misleading test suite",
                    "Replace implementation-coupled assertions with behavioral evidence.",
                    "A revised test suite and a defect explanation.",
                    "False positives are removed",
                    "Failure messages are actionable",
                    "Edge cases are represented",
                ),
            ),
        ),
        CompetencyDefinition(
            "git",
            "Git collaboration",
            "delivery",
            "Work safely with branches, commits, reviews, and conflict resolution.",
            7,
            (
                _activity(
                    "Prepare a reviewable change set",
                    "Turn mixed local work into a coherent commit sequence and pull request.",
                    "A commit plan, clean history, and reviewer-oriented PR summary.",
                    "Commits are independently understandable",
                    "Generated noise is excluded",
                    "The PR states evidence and risk",
                ),
                _activity(
                    "Resolve a realistic merge conflict",
                    "Preserve both intended behaviors and prove the resolved result.",
                    "Resolved files, validation commands, and a conflict rationale.",
                    "No side is accepted blindly",
                    "Tests prove the combined behavior",
                    "History remains understandable",
                ),
            ),
        ),
        CompetencyDefinition(
            "docker",
            "Docker and runtime packaging",
            "delivery",
            (
                "Package services reproducibly with minimal runtime privileges "
                "and clear configuration."
            ),
            8,
            (
                _activity(
                    "Containerize a FastAPI service",
                    "Produce a deterministic non-root runtime image.",
                    "Dockerfile, ignore file, health check, and run instructions.",
                    "The image runs as non-root",
                    "Build inputs are bounded",
                    "Configuration is injected at runtime",
                ),
                _activity(
                    "Harden a development container",
                    "Reduce image size and remove build-only tools from runtime.",
                    "A multi-stage Dockerfile and measured comparison.",
                    "Runtime dependencies are minimal",
                    "Secrets are not baked into layers",
                    "The final image still passes health checks",
                ),
            ),
        ),
        CompetencyDefinition(
            "ci",
            "Continuous integration",
            "delivery",
            "Create deterministic quality gates that produce auditable evidence.",
            7,
            (
                _activity(
                    "Build a fail-closed CI workflow",
                    "Gate formatting, linting, typing, tests, and artifact creation.",
                    "A pinned workflow and evidence-oriented README section.",
                    "Actions are pinned",
                    "Required checks cannot be skipped silently",
                    "Artifacts are sanitized",
                ),
                _activity(
                    "Diagnose a flaky pipeline",
                    "Separate environmental instability from product defects.",
                    "A root-cause report and bounded workflow repair.",
                    "The failure is reproducible or classified",
                    "Retries do not mask deterministic defects",
                    "The repair has a regression check",
                ),
            ),
        ),
        CompetencyDefinition(
            "debugging",
            "Debugging and observability",
            "operations",
            "Use evidence, logs, traces, and controlled experiments to isolate failures.",
            10,
            (
                _activity(
                    "Investigate a failing service request",
                    (
                        "Trace one request from symptom to root cause without leaking "
                        "confidential data."
                    ),
                    "An incident timeline, evidence table, fix, and regression test.",
                    "Correlation is preserved",
                    "Sensitive values are excluded",
                    "The root cause is distinguished from symptoms",
                ),
                _activity(
                    "Design bounded diagnostic events",
                    (
                        "Define useful operational events with low cardinality and explicit "
                        "privacy rules."
                    ),
                    "An event schema, examples, and volume budget.",
                    "Fields have stable semantics",
                    "Untrusted text is excluded",
                    "Event volume is bounded",
                ),
            ),
        ),
        CompetencyDefinition(
            "communication",
            "Engineering communication",
            "professional",
            "Explain decisions, trade-offs, risks, and validation evidence clearly.",
            7,
            (
                _activity(
                    "Write an implementation decision record",
                    "Explain a backend design choice to engineers and reviewers.",
                    "A concise ADR with context, options, decision, and consequences.",
                    "Alternatives are represented fairly",
                    "The decision is testable",
                    "Risks and reversibility are explicit",
                ),
                _activity(
                    "Present a technical incident update",
                    (
                        "Communicate impact, evidence, mitigation, and next action without "
                        "speculation."
                    ),
                    "A stakeholder update and technical appendix.",
                    "Known facts and hypotheses are separated",
                    "Impact is concrete",
                    "The next verification step is explicit",
                ),
            ),
        ),
    ),
)

ROLE_CATALOG: Final = {PYTHON_BACKEND_ROLE.identifier: PYTHON_BACKEND_ROLE}
