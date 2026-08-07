"use client";

import { type FormEvent, useState } from "react";

import { startAssessment, submitAssessment } from "../../lib/platform-client";
import type { AssessmentAttemptView, AssessmentSubmissionView } from "../../lib/learning-contract";
import { useCareerApp } from "./app-provider";
import { NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

export function AssessmentsView() {
  const { plan, commitPlan } = useCareerApp();
  const [attempt, setAttempt] = useState<AssessmentAttemptView | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AssessmentSubmissionView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (plan === null) {
    return <NoPlan />;
  }

  const begin = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const nextAttempt = await startAssessment(plan.state_token);
      setAttempt(nextAttempt);
      setAnswers({});
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The assessment could not start.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (attempt === null) {
      return;
    }
    if (attempt.questions.some((question) => answers[question.id] === undefined)) {
      setError("Answer every question before submitting the calibration.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const nextResult = await submitAssessment({
        state_token: plan.state_token,
        attempt_token: attempt.attempt_token,
        answers: attempt.questions.map((question) => ({
          question_id: question.id,
          option_id: answers[question.id] ?? ""
        }))
      });
      setResult(nextResult);
      setAttempt(null);
      setAnswers({});
      commitPlan(nextResult.plan);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The assessment could not be submitted.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Assessments"
        title="Calibrate self-report with answer-hidden checks."
        description="Assessments do not replace projects. They add an objective signal to the same competency model and can immediately change the next work selected by the roadmap."
        action={
          attempt === null ? (
            <button className="button button-primary" disabled={busy} type="button" onClick={() => void begin()}>
              {busy ? "Starting…" : "Start calibration"}
            </button>
          ) : undefined
        }
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Calibration history</span>
          <h2>{plan.assessment_history.length} completed attempts</h2>
          {plan.assessment_history.length === 0 ? (
            <p>No calibration has been completed yet.</p>
          ) : (
            <ul className={styles.timeline}>
              {[...plan.assessment_history].reverse().map((record) => (
                <li key={record.attempt_id}>
                  <time dateTime={record.submitted_at}>{record.score_percent}%</time>
                  <div>
                    <strong>{record.correct_count}/{record.total_count} correct</strong>
                    <p>{Object.keys(record.competency_scores).length} competencies calibrated · {record.bank_version}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Current assessment signal</span>
          <div className={styles.readinessBand}>
            <div>
              <strong>Assessment coverage</strong>
              <p>Share of the role graph with an objective calibration signal.</p>
            </div>
            <span>{plan.assessment_coverage_percent}%</span>
          </div>
          {result !== null ? (
            <div>
              <p className={styles.label}>Latest result</p>
              <h2>{result.score_percent}% · {result.correct_count}/{result.total_count}</h2>
              <ul className={styles.list}>
                {result.feedback.map((item) => (
                  <li key={item.question_id}>
                    <span className={styles.itemTitle}>
                      <strong>{item.correct ? "Correct" : "Needs review"}</strong>
                      <small>{item.explanation}</small>
                    </span>
                    <span className={styles.score}>{item.correct ? "✓" : "×"}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      </section>

      {attempt !== null ? (
        <article className={styles.formCard}>
          <span className={styles.label}>Active calibration · expires {new Date(attempt.expires_at).toLocaleTimeString()}</span>
          <form className={styles.form} onSubmit={submit}>
            {attempt.questions.map((question, index) => (
              <fieldset className={styles.question} key={question.id}>
                <legend>
                  {index + 1}. {question.competency_name}
                </legend>
                <h3>{question.prompt}</h3>
                <div className={styles.options}>
                  {question.options.map((option) => (
                    <label className={styles.option} key={option.id}>
                      <input
                        type="radio"
                        name={question.id}
                        value={option.id}
                        checked={answers[question.id] === option.id}
                        onChange={() => setAnswers((current) => ({ ...current, [question.id]: option.id }))}
                      />
                      <span>{option.text}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <div className={styles.actions}>
              <button className="button button-primary" disabled={busy} type="submit">
                {busy ? "Scoring…" : "Submit calibration"}
              </button>
              <button className="button button-quiet" disabled={busy} type="button" onClick={() => setAttempt(null)}>
                Cancel
              </button>
            </div>
          </form>
        </article>
      ) : null}
    </div>
  );
}
