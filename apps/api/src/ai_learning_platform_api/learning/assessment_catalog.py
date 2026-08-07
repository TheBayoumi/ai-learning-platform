"""Versioned bounded assessment bank for provisional competency calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class AssessmentOptionDefinition:
    """One selectable answer without transport concerns."""

    identifier: str
    text: str


@dataclass(frozen=True, slots=True)
class AssessmentQuestionDefinition:
    """A single-choice calibration question with a server-only answer."""

    identifier: str
    competency_id: str
    prompt: str
    options: tuple[AssessmentOptionDefinition, ...]
    correct_option_id: str
    explanation: str


def _option(identifier: str, text: str) -> AssessmentOptionDefinition:
    return AssessmentOptionDefinition(identifier=identifier, text=text)


def _question(
    identifier: str,
    competency_id: str,
    prompt: str,
    options: tuple[str, str, str, str],
    correct_option_id: str,
    explanation: str,
) -> AssessmentQuestionDefinition:
    return AssessmentQuestionDefinition(
        identifier=identifier,
        competency_id=competency_id,
        prompt=prompt,
        options=tuple(
            _option(option_id, text)
            for option_id, text in zip(("a", "b", "c", "d"), options, strict=True)
        ),
        correct_option_id=correct_option_id,
        explanation=explanation,
    )


# The original ten-question bank remains byte-compatible at the question-ID/answer boundary.
# New role-specific questions are additive, so existing signed Python-backend attempts remain valid.
ASSESSMENT_BANK_VERSION: Final = "2026.07-calibration-1"

ASSESSMENT_QUESTIONS: Final = (
    _question(
        "python-mutable-default",
        "python",
        (
            "A function appends to a list supplied through a default argument, and later calls "
            "unexpectedly contain values from earlier calls. What is the best correction?"
        ),
        (
            "Copy the default list at module import time.",
            "Use None as the default and create a new list inside the function.",
            "Declare the list global so all calls share it deliberately.",
            "Convert the list to a tuple after every append.",
        ),
        "b",
        (
            "Mutable default arguments are created once at function definition time. A sentinel "
            "such as None allows each call to create independent mutable state."
        ),
    ),
    _question(
        "fastapi-domain-boundary",
        "fastapi",
        (
            "A FastAPI route validates a request, calculates pricing, writes data, and translates "
            "every exception itself. Which refactoring most improves testability?"
        ),
        (
            "Move all code into a larger router module.",
            "Put pricing rules in Pydantic validators.",
            "Delegate domain decisions to a typed service behind an explicit adapter.",
            "Replace exceptions with print statements.",
        ),
        "c",
        (
            "The route should own transport validation and response mapping while a typed service "
            "owns business decisions and adapters own external side effects."
        ),
    ),
    _question(
        "postgresql-integrity",
        "postgresql",
        (
            "An enrollment row must never reference a learner that does not exist. Which database "
            "mechanism should enforce this invariant?"
        ),
        (
            "A foreign-key constraint.",
            "A comment on the learner_id column.",
            "An application log warning.",
            "A non-unique index only.",
        ),
        "a",
        (
            "A foreign key lets PostgreSQL enforce referential integrity for every writer, not "
            "only for one application code path."
        ),
    ),
    _question(
        "rest-idempotency",
        "rest",
        (
            "A client retries the same request after a timeout. Which operation is expected to be "
            "idempotent when it replaces the complete state of a known resource?"
        ),
        (
            "POST /orders",
            "PUT /profiles/42",
            "POST /payments/charge",
            "CONNECT /profiles/42",
        ),
        "b",
        (
            "PUT to a known resource URI is idempotent: repeating the same complete replacement "
            "should produce the same intended resource state."
        ),
    ),
    _question(
        "testing-observable-behavior",
        "testing",
        (
            "A unit test fails whenever a private helper is renamed although public behavior is "
            "unchanged. What is the strongest repair?"
        ),
        (
            "Assert observable outputs and boundary interactions instead.",
            "Make every private helper public.",
            "Disable the test permanently.",
            "Assert the exact source-code line number.",
        ),
        "a",
        (
            "Behavioral tests should protect externally meaningful outcomes rather than incidental "
            "implementation structure."
        ),
    ),
    _question(
        "git-shared-history",
        "git",
        (
            "A commit already exists on a shared protected branch. Which action is safest when the "
            "change must be undone without rewriting collaborators' history?"
        ),
        (
            "Force-push the parent commit.",
            "Delete the remote branch.",
            "Create a revert commit.",
            "Amend the shared commit locally only.",
        ),
        "c",
        (
            "A revert records a new inverse change and preserves shared history; force rewriting a "
            "published protected branch disrupts collaborators."
        ),
    ),
    _question(
        "docker-runtime-hardening",
        "docker",
        "Which Docker design best keeps compilers and build secrets out of the runtime image?",
        (
            "Use one stage and delete files in the final command.",
            "Use a multi-stage build and copy runtime artifacts into a non-root image.",
            "Store secrets in environment variables during image build.",
            "Run the final container as root for compatibility.",
        ),
        "b",
        (
            "A multi-stage build separates build tooling from the final image, while a non-root "
            "runtime reduces the impact of a compromise."
        ),
    ),
    _question(
        "ci-supply-chain",
        "ci",
        (
            "Which workflow practice most directly reduces supply-chain drift in third-party CI "
            "actions?"
        ),
        (
            "Reference the action's default branch.",
            "Pin the action to an immutable commit SHA.",
            "Retry every failed job three times.",
            "Print all environment variables for debugging.",
        ),
        "b",
        (
            "An immutable commit SHA prevents a mutable tag or branch from silently changing the "
            "executed third-party code."
        ),
    ),
    _question(
        "debugging-correlation",
        "debugging",
        (
            "Several services handle one failing request. Which evidence most reliably connects "
            "their logs without recording the user's confidential payload?"
        ),
        (
            "A shared bounded correlation identifier.",
            "The complete request body in every log line.",
            "A random message written by each service.",
            "Only the server's local wall-clock second.",
        ),
        "a",
        (
            "A propagated correlation identifier links events across services while avoiding the "
            "need to duplicate confidential request content."
        ),
    ),
    _question(
        "communication-facts-hypotheses",
        "communication",
        "During an incident, the root cause is not yet known. Which update is most accurate?",
        (
            "State a confident root cause so stakeholders are reassured.",
            "Separate confirmed impact, current hypotheses, mitigation, and next check.",
            "Share every raw log line without interpretation.",
            "Wait until the incident is fully resolved before communicating.",
        ),
        "b",
        (
            "Separating known facts from hypotheses prevents speculation from becoming an asserted "
            "fact while still giving stakeholders actionable status."
        ),
    ),
    _question(
        "llm-output-boundary",
        "llm-applications",
        (
            "An LLM returns JSON that will update application state. Which boundary is most "
            "important before the update occurs?"
        ),
        (
            "Trust the JSON whenever the model used a low temperature.",
            "Validate it against a deterministic schema and authorization rules.",
            "Store the raw response as the authoritative state.",
            "Ask the model whether its own response is safe.",
        ),
        "b",
        (
            "Model output remains untrusted input. Deterministic schema and authorization checks "
            "must mediate any authoritative state mutation."
        ),
    ),
    _question(
        "rag-retrieval-miss",
        "rag",
        (
            "A RAG answer is wrong because the relevant source never appeared in "
            "retrieved context. Which subsystem should be investigated first?"
        ),
        (
            "Retrieval and ranking quality.",
            "The final answer font.",
            "The model's sampling temperature only.",
            "The browser cache.",
        ),
        "a",
        (
            "When necessary evidence was never retrieved, retrieval or ranking is "
            "the first failure boundary; generation cannot cite context it never received."
        ),
    ),
    _question(
        "ai-eval-hidden-set",
        "ai-evaluation",
        (
            "Why should an AI feature keep a representative evaluation set hidden from prompt and "
            "workflow tuning?"
        ),
        (
            "To make failures harder to debug.",
            "To estimate generalization instead of optimizing directly to known cases.",
            "To avoid defining task-specific success criteria.",
            "To eliminate the need for regression thresholds.",
        ),
        "b",
        (
            "A held-out set gives a less biased signal of whether changes generalize beyond the "
            "examples used during tuning."
        ),
    ),
    _question(
        "data-modeling-grain",
        "data-modeling",
        (
            "Before defining dimensions and metrics for an analytical fact table, what must be "
            "made explicit first?"
        ),
        (
            "The row grain represented by one fact record.",
            "The dashboard background color.",
            "The longest column name.",
            "The BI tool used by one analyst.",
        ),
        "a",
        (
            "Explicit grain prevents incompatible events and metrics from being mixed into the "
            "same fact table and anchors keys and aggregation semantics."
        ),
    ),
    _question(
        "pipeline-idempotency",
        "data-pipelines",
        (
            "A batch ingestion task retries after failing halfway through. Which property prevents "
            "the retry from duplicating already accepted records?"
        ),
        (
            "Idempotent writes or deterministic deduplication keys.",
            "A longer task name.",
            "Disabling all retries.",
            "Increasing log verbosity only.",
        ),
        "a",
        (
            "Idempotent writes or stable deduplication identity let retries converge on the same "
            "accepted data state instead of multiplying records."
        ),
    ),
    _question(
        "data-quality-freshness",
        "data-quality",
        (
            "A daily dataset is complete for old dates but has not received today's expected load. "
            "Which quality dimension detects this most directly?"
        ),
        (
            "Freshness.",
            "Uniqueness.",
            "Column alphabetical order.",
            "Compression ratio.",
        ),
        "a",
        (
            "Freshness checks whether data arrived within the expected time window, independently "
            "from whether historical rows are complete or unique."
        ),
    ),
)

QUESTION_BY_ID: Final = {question.identifier: question for question in ASSESSMENT_QUESTIONS}
QUESTIONS_BY_COMPETENCY: Final = {
    question.competency_id: question for question in ASSESSMENT_QUESTIONS
}
