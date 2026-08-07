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


ASSESSMENT_BANK_VERSION: Final = "2026.08-calibration-2"

ASSESSMENT_QUESTIONS: Final = (
    AssessmentQuestionDefinition(
        identifier="python-mutable-default",
        competency_id="python",
        prompt=(
            "A function appends to a list supplied through a default argument, and later calls "
            "unexpectedly contain values from earlier calls. What is the best correction?"
        ),
        options=(
            _option("a", "Copy the default list at module import time."),
            _option("b", "Use None as the default and create a new list inside the function."),
            _option("c", "Declare the list global so all calls share it deliberately."),
            _option("d", "Convert the list to a tuple after every append."),
        ),
        correct_option_id="b",
        explanation=(
            "Mutable default arguments are created once at function definition time. A sentinel "
            "such as None allows each call to create independent mutable state."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="fastapi-domain-boundary",
        competency_id="fastapi",
        prompt=(
            "A FastAPI route validates an HTTP request, calculates pricing rules, writes data, "
            "and translates every exception itself. Which refactoring most improves testability?"
        ),
        options=(
            _option("a", "Move all code into a larger router module."),
            _option("b", "Put pricing rules in Pydantic validators."),
            _option("c", "Delegate domain decisions to a typed service behind an explicit adapter."),
            _option("d", "Replace exceptions with print statements."),
        ),
        correct_option_id="c",
        explanation=(
            "The route should own transport validation and response mapping while a typed service "
            "owns business decisions and adapters own external side effects."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="postgresql-integrity",
        competency_id="postgresql",
        prompt=(
            "An enrollment row must never reference a learner that does not exist. Which database "
            "mechanism should enforce this invariant?"
        ),
        options=(
            _option("a", "A foreign-key constraint."),
            _option("b", "A comment on the learner_id column."),
            _option("c", "An application log warning."),
            _option("d", "A non-unique index only."),
        ),
        correct_option_id="a",
        explanation=(
            "A foreign key lets PostgreSQL enforce referential integrity for every writer, not "
            "only for one application code path."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="rest-idempotency",
        competency_id="rest",
        prompt=(
            "A client retries the same request after a timeout. Which operation is expected to be "
            "idempotent when it replaces the complete state of a known resource?"
        ),
        options=(
            _option("a", "POST /orders"),
            _option("b", "PUT /profiles/42"),
            _option("c", "POST /payments/charge"),
            _option("d", "CONNECT /profiles/42"),
        ),
        correct_option_id="b",
        explanation=(
            "PUT to a known resource URI is defined as idempotent: repeating the same complete "
            "replacement should produce the same intended resource state."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="testing-observable-behavior",
        competency_id="testing",
        prompt=(
            "A unit test fails whenever a private helper is renamed although public behavior is "
            "unchanged. What is the strongest repair?"
        ),
        options=(
            _option("a", "Assert observable outputs and boundary interactions instead."),
            _option("b", "Make every private helper public."),
            _option("c", "Disable the test permanently."),
            _option("d", "Assert the exact source-code line number."),
        ),
        correct_option_id="a",
        explanation=(
            "Behavioral tests should protect externally meaningful outcomes rather than incidental "
            "implementation structure."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="git-shared-history",
        competency_id="git",
        prompt=(
            "A commit already exists on a shared protected branch. Which action is safest when the "
            "change must be undone without rewriting collaborators' history?"
        ),
        options=(
            _option("a", "Force-push the parent commit."),
            _option("b", "Delete the remote branch."),
            _option("c", "Create a revert commit."),
            _option("d", "Amend the shared commit locally only."),
        ),
        correct_option_id="c",
        explanation=(
            "A revert records a new inverse change and preserves shared history; force rewriting a "
            "published protected branch disrupts collaborators."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="docker-runtime-hardening",
        competency_id="docker",
        prompt=(
            "Which Docker design best keeps compilers and build secrets out of the runtime image?"
        ),
        options=(
            _option("a", "Use one stage and delete files in the final command."),
            _option("b", "Use a multi-stage build and copy only runtime artifacts into a non-root image."),
            _option("c", "Store secrets in environment variables during image build."),
            _option("d", "Run the final container as root for compatibility."),
        ),
        correct_option_id="b",
        explanation=(
            "A multi-stage build separates build tooling from the final image, while a non-root "
            "runtime reduces the impact of a compromise."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="ci-supply-chain",
        competency_id="ci",
        prompt=(
            "Which workflow practice most directly reduces supply-chain drift in third-party CI "
            "actions?"
        ),
        options=(
            _option("a", "Reference the action's default branch."),
            _option("b", "Pin the action to an immutable commit SHA."),
            _option("c", "Retry every failed job three times."),
            _option("d", "Print all environment variables for debugging."),
        ),
        correct_option_id="b",
        explanation=(
            "An immutable commit SHA prevents a mutable tag or branch from silently changing the "
            "executed third-party code."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="debugging-correlation",
        competency_id="debugging",
        prompt=(
            "Several services handle one failing request. Which evidence most reliably connects "
            "their logs without recording the user's confidential payload?"
        ),
        options=(
            _option("a", "A shared bounded correlation identifier."),
            _option("b", "The complete request body in every log line."),
            _option("c", "A random message written by each service."),
            _option("d", "Only the server's local wall-clock second."),
        ),
        correct_option_id="a",
        explanation=(
            "A propagated correlation identifier links events across services while avoiding the "
            "need to duplicate confidential request content."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="communication-facts-hypotheses",
        competency_id="communication",
        prompt=(
            "During an incident, the root cause is not yet known. Which update is most accurate?"
        ),
        options=(
            _option("a", "State a confident root cause so stakeholders are reassured."),
            _option("b", "Separate confirmed impact, current hypotheses, mitigation, and next check."),
            _option("c", "Share every raw log line without interpretation."),
            _option("d", "Wait until the incident is fully resolved before communicating."),
        ),
        correct_option_id="b",
        explanation=(
            "Separating known facts from hypotheses prevents speculation from becoming an asserted "
            "fact while still giving stakeholders actionable status."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="llm-output-boundary",
        competency_id="llm-applications",
        prompt=(
            "An LLM returns JSON that will be used to update application state. Which boundary is "
            "most important before the update occurs?"
        ),
        options=(
            _option("a", "Trust the JSON whenever the model used a low temperature."),
            _option("b", "Validate it against a deterministic schema and authorization rules."),
            _option("c", "Store the raw response as the authoritative state."),
            _option("d", "Ask the model whether its own response is safe."),
        ),
        correct_option_id="b",
        explanation=(
            "Model output remains untrusted input. Deterministic schema and authorization checks "
            "must mediate any authoritative state mutation."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="rag-retrieval-miss",
        competency_id="rag",
        prompt=(
            "A RAG answer is wrong because the relevant source never appeared in retrieved context. "
            "Which subsystem should be investigated first?"
        ),
        options=(
            _option("a", "Retrieval and ranking quality."),
            _option("b", "The final answer font."),
            _option("c", "The model's sampling temperature only."),
            _option("d", "The browser cache."),
        ),
        correct_option_id="a",
        explanation=(
            "When the necessary evidence was never retrieved, retrieval or ranking is the first "
            "failure boundary; generation cannot cite context it never received."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="ai-eval-hidden-set",
        competency_id="ai-evaluation",
        prompt=(
            "Why should an AI feature keep a representative evaluation set hidden from prompt and "
            "workflow tuning?"
        ),
        options=(
            _option("a", "To make failures harder to debug."),
            _option("b", "To estimate generalization instead of optimizing directly to known cases."),
            _option("c", "To avoid defining task-specific success criteria."),
            _option("d", "To eliminate the need for regression thresholds."),
        ),
        correct_option_id="b",
        explanation=(
            "A held-out set gives a less biased signal of whether changes generalize beyond the "
            "examples used during tuning."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="data-modeling-grain",
        competency_id="data-modeling",
        prompt=(
            "Before defining dimensions and metrics for an analytical fact table, what must be "
            "made explicit first?"
        ),
        options=(
            _option("a", "The row grain represented by one fact record."),
            _option("b", "The dashboard background color."),
            _option("c", "The longest column name."),
            _option("d", "The BI tool used by one analyst."),
        ),
        correct_option_id="a",
        explanation=(
            "Explicit grain prevents incompatible events and metrics from being mixed into the "
            "same fact table and anchors keys and aggregation semantics."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="pipeline-idempotency",
        competency_id="data-pipelines",
        prompt=(
            "A batch ingestion task retries after failing halfway through. Which property prevents "
            "the retry from duplicating already accepted records?"
        ),
        options=(
            _option("a", "Idempotent writes or deterministic deduplication keys."),
            _option("b", "A longer task name."),
            _option("c", "Disabling all retries."),
            _option("d", "Increasing log verbosity only."),
        ),
        correct_option_id="a",
        explanation=(
            "Idempotent writes or stable deduplication identity let retries converge on the same "
            "accepted data state instead of multiplying records."
        ),
    ),
    AssessmentQuestionDefinition(
        identifier="data-quality-freshness",
        competency_id="data-quality",
        prompt=(
            "A daily dataset is complete for old dates but has not received today's expected load. "
            "Which quality dimension detects this most directly?"
        ),
        options=(
            _option("a", "Freshness."),
            _option("b", "Uniqueness."),
            _option("c", "Column alphabetical order."),
            _option("d", "Compression ratio."),
        ),
        correct_option_id="a",
        explanation=(
            "Freshness checks whether data arrived within the expected time window, independently "
            "from whether historical rows are complete or unique."
        ),
    ),
)

QUESTION_BY_ID: Final = {question.identifier: question for question in ASSESSMENT_QUESTIONS}
QUESTIONS_BY_COMPETENCY: Final = {
    question.competency_id: question for question in ASSESSMENT_QUESTIONS
}
