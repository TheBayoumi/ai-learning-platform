"""Temporarily apply the assessment integration before committing verified output."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent, indent

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "apps/api/src/ai_learning_platform_api/learning/service.py"
TEST_PATH = ROOT / "apps/api/tests/test_assessment_api.py"


def apply_service_integration() -> None:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    if "AssessmentCalibrationEngine" in text:
        return

    text = text.replace(
        "from pydantic import ValidationError\n\n",
        "from pydantic import ValidationError\n\n"
        "from ai_learning_platform_api.learning.assessment import (\n"
        "    AssessmentCalibrationEngine,\n"
        ")\n",
        1,
    )
    text = text.replace(
        "    ActivityView,\n",
        "    ActivityView,\n"
        "    AssessmentAttemptView,\n"
        "    AssessmentStartRequest,\n"
        "    AssessmentSubmissionView,\n"
        "    AssessmentSubmitRequest,\n",
        1,
    )
    text = text.replace(
        "_MAX_EVIDENCE_HISTORY = 24\n",
        "_MAX_EVIDENCE_HISTORY = 24\n_MAX_ASSESSMENT_HISTORY = 12\n",
        1,
    )
    text = text.replace(
        "        self._id_factory = id_factory if id_factory is not None else uuid4\n",
        "        self._id_factory = id_factory if id_factory is not None else uuid4\n"
        "        self._assessment = AssessmentCalibrationEngine(\n"
        "            secret, clock=self._clock, id_factory=self._id_factory\n"
        "        )\n",
        1,
    )
    text = text.replace("            schema_version=2,\n", "            schema_version=3,\n", 1)

    methods = indent(
        dedent(
            '''
            def start_assessment(
                self, request: AssessmentStartRequest
            ) -> AssessmentAttemptView:
                """Issue an expiring calibration attempt for current priority gaps."""
                state = self._codec.decode(request.state_token)
                role = ROLE_CATALOG.get(state.target_role)
                if role is None:
                    raise InvalidStateTokenError
                effective_mastery = self._effective_mastery_values(
                    role, state.mastery, state.assessment_scores
                )
                priorities = self._rank_competencies(
                    role,
                    effective_mastery,
                    state.focus_competency_ids,
                )[: request.question_count]
                return self._assessment.start(
                    state=state,
                    role=role,
                    competency_ids=[item.identifier for item in priorities],
                )

            def submit_assessment(
                self, request: AssessmentSubmitRequest
            ) -> AssessmentSubmissionView:
                """Score a calibration attempt and regenerate assessment-informed work."""
                state = self._codec.decode(request.state_token)
                role = ROLE_CATALOG.get(state.target_role)
                if role is None:
                    raise InvalidStateTokenError
                outcome = self._assessment.score(state=state, role=role, request=request)
                assessment_scores = dict(state.assessment_scores)
                assessment_scores.update(outcome.competency_scores)
                effective_mastery = self._effective_mastery_values(
                    role, state.mastery, assessment_scores
                )
                revision = state.plan_revision + 1
                pending_reviews = [
                    activity
                    for activity in state.activities
                    if activity.kind == "review"
                    and activity.id not in state.completed_activity_ids
                ]
                build_activities = self._generate_build_activities(
                    role=role,
                    mastery=effective_mastery,
                    weekly_hours=state.weekly_hours,
                    focus_competency_ids=state.focus_competency_ids,
                    learner_name=state.learner_name,
                    experience_summary=state.experience_summary,
                    seed=self._learner_seed(
                        state.learner_name,
                        state.target_role,
                        f"{state.experience_summary}|assessment:{outcome.record.attempt_id}",
                    ),
                    generation=revision,
                )
                updated = state.model_copy(
                    update={
                        "schema_version": 3,
                        "sequence": state.sequence + 1,
                        "plan_revision": revision,
                        "assessment_scores": assessment_scores,
                        "assessment_history": [*state.assessment_history, outcome.record][
                            -_MAX_ASSESSMENT_HISTORY:
                        ],
                        "activities": [*pending_reviews, *build_activities],
                    }
                )
                plan = self._project(updated, role)
                return AssessmentSubmissionView(
                    score_percent=outcome.record.score_percent,
                    correct_count=outcome.record.correct_count,
                    total_count=outcome.record.total_count,
                    feedback=list(outcome.feedback),
                    plan=plan,
                )

            '''
        ),
        "    ",
    )
    text = text.replace("    def complete_activity(", methods + "    def complete_activity(", 1)
    text = text.replace('"schema_version": 2,', '"schema_version": 3,')
    text = text.replace(
        "            mastery=state.mastery,\n",
        "            mastery=self._effective_mastery_values(\n"
        "                role, state.mastery, state.assessment_scores\n"
        "            ),\n",
        1,
    )
    text = text.replace(
        "        priorities = self._rank_competencies(\n"
        "            role,\n"
        "            state.mastery,\n"
        "            state.focus_competency_ids,\n"
        "        )[:4]\n",
        "        effective_mastery = self._effective_mastery_values(\n"
        "            role, state.mastery, state.assessment_scores\n"
        "        )\n"
        "        priorities = self._rank_competencies(\n"
        "            role,\n"
        "            effective_mastery,\n"
        "            state.focus_competency_ids,\n"
        "        )[:4]\n",
        1,
    )
    weighted_pattern = re.compile(
        r"        weighted_mastery = sum\(\n"
        r"            state\.mastery\.get\(item\.identifier, 0\) \* item\.weight\n"
        r"            for item in role\.competencies\n"
        r"        \)\n"
        r"        readiness = round\(weighted_mastery / total_weight\)\n"
    )
    text = weighted_pattern.sub(
        "        weighted_evidence_mastery = sum(\n"
        "            state.mastery.get(item.identifier, 0) * item.weight\n"
        "            for item in role.competencies\n"
        "        )\n"
        "        weighted_effective_mastery = sum(\n"
        "            effective_mastery.get(item.identifier, 0) * item.weight\n"
        "            for item in role.competencies\n"
        "        )\n"
        "        evidence_readiness = round(weighted_evidence_mastery / total_weight)\n"
        "        readiness = round(weighted_effective_mastery / total_weight)\n"
        "        assessment_coverage = round(\n"
        "            (len(state.assessment_scores) / len(role.competencies)) * 100\n"
        "        )\n",
        text,
        count=1,
    )
    text = text.replace(
        "            readiness_percent=readiness,\n",
        "            readiness_percent=readiness,\n"
        "            evidence_readiness_percent=evidence_readiness,\n"
        "            assessment_coverage_percent=assessment_coverage,\n",
        1,
    )
    text = text.replace(
        "                    mastery_percent=state.mastery.get(item.identifier, 0),\n"
        "                    gap_percent=100 - state.mastery.get(item.identifier, 0),\n",
        "                    mastery_percent=state.mastery.get(item.identifier, 0),\n"
        "                    effective_percent=effective_mastery.get(item.identifier, 0),\n"
        "                    assessment_percent=state.assessment_scores.get(item.identifier),\n"
        "                    gap_percent=100 - effective_mastery.get(item.identifier, 0),\n",
        1,
    )
    text = text.replace(
        "            evidence_history=list(state.evidence_history[-12:]),\n",
        "            evidence_history=list(state.evidence_history[-12:]),\n"
        "            assessment_history=list(state.assessment_history[-8:]),\n",
        1,
    )

    helper = indent(
        dedent(
            '''
            @staticmethod
            def _effective_mastery_values(
                role: RoleDefinition,
                mastery: dict[str, int],
                assessment_scores: dict[str, int],
            ) -> dict[str, int]:
                """Blend evidence and calibration without overstating either signal."""
                return {
                    competency.identifier: (
                        round(
                            (mastery.get(competency.identifier, 0) * 0.7)
                            + (assessment_scores[competency.identifier] * 0.3)
                        )
                        if competency.identifier in assessment_scores
                        else mastery.get(competency.identifier, 0)
                    )
                    for competency in role.competencies
                }

            '''
        ),
        "    ",
    )
    text = text.replace(
        "    def _generate_build_activities(",
        helper + "    def _generate_build_activities(",
        1,
    )
    SERVICE_PATH.write_text(text, encoding="utf-8", newline="\n")

    required_markers = (
        "def start_assessment(",
        "def submit_assessment(",
        "def _effective_mastery_values(",
        "evidence_readiness_percent=evidence_readiness",
        "assessment_history=list(state.assessment_history[-8:])",
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise RuntimeError(f"assessment integration markers missing: {missing}")


def clean_test_import() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")
    if "    ReplanRequest,\n" not in text:
        text = text.replace(
            "    PlanRequest,\n",
            "    PlanRequest,\n    ReplanRequest,\n",
            1,
        )
    dynamic_pattern = re.compile(
        r"    replanned = service\.replan\(\n"
        r"        __import__\([\s\S]*?"
        r"    \)\n"
        r"(?=    try:)"
    )
    direct = dedent(
        '''
        replanned = service.replan(
            ReplanRequest(
                state_token=plan.state_token,
                weekly_hours=8,
                focus_competency_ids=[],
            )
        )
        '''
    )
    TEST_PATH.write_text(
        dynamic_pattern.sub(direct, text, count=1),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    apply_service_integration()
    clean_test_import()
