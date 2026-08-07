"""Versioned career-role profiles used by the adaptive learning engine."""

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


def _competency(
    identifier: str,
    name: str,
    category: str,
    description: str,
    weight: int,
    first: ActivityTemplate,
    second: ActivityTemplate,
) -> CompetencyDefinition:
    return CompetencyDefinition(
        identifier=identifier,
        name=name,
        category=category,
        description=description,
        weight=weight,
        activities=(first, second),
    )


PYTHON: Final = _competency(
    "python",
    "Python engineering",
    "language",
    "Write maintainable typed Python with clear boundaries and error handling.",
    14,
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
)

FASTAPI: Final = _competency(
    "fastapi",
    "FastAPI service design",
    "backend",
    "Design validated HTTP APIs with explicit contracts and dependency boundaries.",
    13,
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
)

POSTGRESQL: Final = _competency(
    "postgresql",
    "PostgreSQL data modeling",
    "data",
    "Model relational data, constraints, indexes, and transactional changes.",
    12,
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
)

REST: Final = _competency(
    "rest",
    "REST API contracts",
    "backend",
    "Choose resources, methods, status codes, pagination, and idempotency deliberately.",
    10,
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
)

TESTING: Final = _competency(
    "testing",
    "Automated testing",
    "quality",
    "Create focused unit, integration, and contract tests that prove behavior.",
    12,
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
)

GIT: Final = _competency(
    "git",
    "Git collaboration",
    "delivery",
    "Work safely with branches, commits, reviews, and conflict resolution.",
    7,
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
)

DOCKER: Final = _competency(
    "docker",
    "Docker and runtime packaging",
    "delivery",
    "Package services reproducibly with minimal runtime privileges and clear configuration.",
    8,
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
)

CI: Final = _competency(
    "ci",
    "Continuous integration",
    "delivery",
    "Create deterministic quality gates that produce auditable evidence.",
    7,
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
)

DEBUGGING: Final = _competency(
    "debugging",
    "Debugging and observability",
    "operations",
    "Use evidence, logs, traces, and controlled experiments to isolate failures.",
    10,
    _activity(
        "Investigate a failing service request",
        "Trace one request from symptom to root cause without leaking confidential data.",
        "An incident timeline, evidence table, fix, and regression test.",
        "Correlation is preserved",
        "Sensitive values are excluded",
        "The root cause is distinguished from symptoms",
    ),
    _activity(
        "Design bounded diagnostic events",
        "Define useful operational events with low cardinality and explicit privacy rules.",
        "An event schema, examples, and volume budget.",
        "Fields have stable semantics",
        "Untrusted text is excluded",
        "Event volume is bounded",
    ),
)

COMMUNICATION: Final = _competency(
    "communication",
    "Engineering communication",
    "professional",
    "Explain decisions, trade-offs, risks, and validation evidence clearly.",
    7,
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
        "Communicate impact, evidence, mitigation, and next action without speculation.",
        "A stakeholder update and technical appendix.",
        "Known facts and hypotheses are separated",
        "Impact is concrete",
        "The next verification step is explicit",
    ),
)

LLM_APPLICATIONS: Final = _competency(
    "llm-applications",
    "LLM application engineering",
    "ai",
    "Build bounded model-backed features with explicit schemas, failures, and cost limits.",
    16,
    _activity(
        "Build a structured LLM feature",
        "Wrap a model call behind a typed contract with bounded context and validation.",
        "A model-backed service, typed response schema, tests, and failure policy.",
        "Input context is bounded",
        "Model output is validated before use",
        "Timeout and cost limits are explicit",
        minutes=120,
    ),
    _activity(
        "Design a model fallback path",
        "Make an AI feature degrade safely when a provider is unavailable or malformed.",
        "A fallback design, implementation, and injected-failure tests.",
        "Provider failures are classified",
        "Fallback behavior is user-safe",
        "No model output mutates authority directly",
    ),
)

RAG: Final = _competency(
    "rag",
    "Retrieval-augmented generation",
    "ai",
    "Design retrieval pipelines that preserve provenance, relevance, and bounded context.",
    16,
    _activity(
        "Build a provenance-first retrieval pipeline",
        "Retrieve a corpus, rank evidence, and answer with source attribution.",
        "Retriever code, evaluation queries, answer citations, and failure analysis.",
        "Retrieved chunks retain source identity",
        "Context has a deterministic size limit",
        "Unsupported answers fail or abstain",
        minutes=150,
    ),
    _activity(
        "Diagnose retrieval quality",
        "Separate retrieval misses from generation errors on a bounded evaluation set.",
        "A labeled query set, retrieval metrics, error taxonomy, and validated improvement.",
        "Retrieval and generation errors are separated",
        "The evaluation set is answer-hidden during tuning",
        "The change is measured against baseline",
    ),
)

AI_EVALUATION: Final = _competency(
    "ai-evaluation",
    "AI evaluation and safety",
    "ai",
    "Evaluate model-backed behavior with datasets, rubrics, adversarial cases, and regressions.",
    17,
    _activity(
        "Create an AI regression suite",
        "Define pass criteria and test a model-backed feature against representative cases.",
        "An evaluation dataset, grader rubric, baseline report, and regression threshold.",
        "Cases cover normal and adversarial inputs",
        "The grader has explicit criteria",
        "Results can compare revisions",
        minutes=150,
    ),
    _activity(
        "Audit an AI feature for unsafe authority",
        "Trace where model output affects state and add deterministic validation boundaries.",
        "A trust-boundary map, threat cases, fixes, and regression tests.",
        "Model output is treated as untrusted",
        "Authoritative mutations have deterministic checks",
        "Sensitive context is minimized",
    ),
)

DATA_MODELING: Final = _competency(
    "data-modeling",
    "Analytical data modeling",
    "data",
    "Turn business concepts into analytical models with explicit grain, keys, and lineage.",
    12,
    _activity(
        "Design an analytics model",
        "Translate a workflow into facts, dimensions, keys, and documented grain.",
        "A model diagram, DDL, lineage note, and representative analytical queries.",
        "Every table has explicit grain",
        "Keys and relationships are defensible",
        "The model supports the stated queries",
        minutes=120,
    ),
    _activity(
        "Refactor a reporting schema",
        "Remove ambiguous grain and duplicated business logic from a reporting dataset.",
        "A before/after model, migration path, and validation queries.",
        "Metric definitions have one source of truth",
        "Historical behavior is preserved or versioned",
        "The migration is reversible",
    ),
)

DATA_PIPELINES: Final = _competency(
    "data-pipelines",
    "Data pipelines and orchestration",
    "data",
    "Build idempotent data workflows with observable retries and bounded backfills.",
    13,
    _activity(
        "Build an idempotent ingestion pipeline",
        "Ingest raw events into modeled tables without duplicating data on retry.",
        "Pipeline code, checkpoint strategy, failure tests, and runbook.",
        "Retries do not duplicate accepted data",
        "Partial failures are recoverable",
        "Operational state is observable",
        minutes=150,
    ),
    _activity(
        "Design a safe backfill",
        "Reprocess a historical interval without corrupting current production data.",
        "A backfill plan, isolation strategy, validation queries, and rollback path.",
        "The affected interval is bounded",
        "Current writes remain safe",
        "Post-backfill reconciliation is explicit",
    ),
)

DATA_QUALITY: Final = _competency(
    "data-quality",
    "Data quality and lineage",
    "quality",
    "Detect broken assumptions with freshness, completeness, uniqueness, and lineage checks.",
    10,
    _activity(
        "Create a data quality contract",
        "Define measurable expectations for one critical dataset and fail visibly on violations.",
        "A quality contract, automated checks, alert thresholds, and incident examples.",
        "Checks map to business impact",
        "Thresholds distinguish warning from failure",
        "Failures identify the affected data window",
    ),
    _activity(
        "Trace a bad metric to source",
        "Use lineage and validation evidence to isolate where a published metric became wrong.",
        "A lineage trace, root-cause timeline, repaired check, and regression case.",
        "The first bad transformation is identified",
        "Downstream symptoms are separated from root cause",
        "A regression check protects the repaired invariant",
    ),
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
        PYTHON,
        FASTAPI,
        POSTGRESQL,
        REST,
        TESTING,
        GIT,
        DOCKER,
        CI,
        DEBUGGING,
        COMMUNICATION,
    ),
)


def _with_weight(source: CompetencyDefinition, weight: int) -> CompetencyDefinition:
    return CompetencyDefinition(
        identifier=source.identifier,
        name=source.name,
        category=source.category,
        description=source.description,
        weight=weight,
        activities=source.activities,
    )


AI_APPLICATION_ROLE: Final = RoleDefinition(
    identifier="ai-application-engineer",
    version="2026.08-provisional-1",
    title="AI Application Engineer",
    summary=(
        "Build production AI features around LLMs and retrieval systems, with strong backend, "
        "evaluation, observability, and safety boundaries."
    ),
    competencies=(
        _with_weight(PYTHON, 12),
        _with_weight(FASTAPI, 8),
        _with_weight(TESTING, 9),
        _with_weight(GIT, 5),
        _with_weight(DOCKER, 5),
        _with_weight(DEBUGGING, 7),
        _with_weight(COMMUNICATION, 5),
        LLM_APPLICATIONS,
        RAG,
        AI_EVALUATION,
    ),
)

DATA_ENGINEER_ROLE: Final = RoleDefinition(
    identifier="data-engineer",
    version="2026.08-provisional-1",
    title="Data Engineer",
    summary=(
        "Design reliable data models and pipelines, operate PostgreSQL-centered workloads, and "
        "prove data quality through automated, observable delivery practices."
    ),
    competencies=(
        _with_weight(PYTHON, 12),
        _with_weight(POSTGRESQL, 15),
        _with_weight(TESTING, 8),
        _with_weight(GIT, 5),
        _with_weight(DOCKER, 6),
        _with_weight(CI, 6),
        _with_weight(DEBUGGING, 8),
        _with_weight(COMMUNICATION, 5),
        DATA_MODELING,
        DATA_PIPELINES,
        DATA_QUALITY,
    ),
)

ROLE_CATALOG: Final = {
    PYTHON_BACKEND_ROLE.identifier: PYTHON_BACKEND_ROLE,
    AI_APPLICATION_ROLE.identifier: AI_APPLICATION_ROLE,
    DATA_ENGINEER_ROLE.identifier: DATA_ENGINEER_ROLE,
}
