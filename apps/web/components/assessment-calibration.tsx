"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  isAssessmentAttemptView,
  isAssessmentSubmissionView,
  readPlatformError,
  type AssessmentAttemptView,
  type AssessmentSubmissionView
} from "../lib/learning-contract";
import {
  PLAN_SAVED_EVENT,
  publishPlanUpdated
} from "../lib/learning-events";
import { LEARNING_SESSION_STORAGE_KEY } from "../lib/learning-session";

interface RequestOptions {
  readonly body: unknown;
}

async function assessmentRequest(
  path: "assessments/start" | "assessments/submit",
  options: RequestOptions
): Promise<unknown> {
  const response = await fetch(`/api/platform/${path}`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json"
    },
    body: JSON.stringify(options.body),
    cache: "no-store",
    credentials: "same-origin"
  });

  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new Error("The calibration service returned an unreadable response.");
  }
  if (!response.ok) {
    throw new Error(readPlatformError(value));
  }
  return value;
}

function formatExpiry(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) {
    return "shortly";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(parsed);
}

export function AssessmentCalibration() {
  const [hasPlan, setHasPlan] = useState(false);
  const [attempt, setAttempt] = useState<AssessmentAttemptView | null>(null);
  const [answers, setAnswers] = useState<Readonly<Record<string, string>>>({});
  const [result, setResult] = useState<AssessmentSubmissionView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refreshAvailability = () => {
      setHasPlan(window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY) !== null);
    };
    const handle = window.setTimeout(refreshAvailability, 0);
    window.addEventListener(PLAN_SAVED_EVENT, refreshAvailability);
    return () => {
      window.clearTimeout(handle);
      window.removeEventListener(PLAN_SAVED_EVENT, refreshAvailability);
    };
  }, []);

  const answeredCount = useMemo(
    () =>
      attempt?.questions.filter((question) => answers[question.id] !== undefined)
        .length ?? 0,
    [answers, attempt]
  );

  const startAssessment = async () => {
    const stateToken = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
    if (stateToken === null) {
      setHasPlan(false);
      setError("Create or resume a learning plan before starting calibration.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const value = await assessmentRequest("assessments/start", {
        body: {
          state_token: stateToken,
          question_count: 4
        }
      });
      if (!isAssessmentAttemptView(value)) {
        throw new Error("The calibration attempt did not match the expected contract.");
      }
      setAttempt(value);
      setAnswers({});
      setResult(null);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The calibration attempt could not be started."
      );
    } finally {
      setBusy(false);
    }
  };

  const submitAssessment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (attempt === null || answeredCount !== attempt.questions.length) {
      setError("Answer every calibration question before submitting.");
      return;
    }
    const stateToken = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
    if (stateToken === null) {
      setHasPlan(false);
      setError("The saved learning plan is no longer available in this browser.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const value = await assessmentRequest("assessments/submit", {
        body: {
          state_token: stateToken,
          attempt_token: attempt.attempt_token,
          answers: attempt.questions.map((question) => ({
            question_id: question.id,
            option_id: answers[question.id]
          }))
        }
      });
      if (!isAssessmentSubmissionView(value)) {
        throw new Error("The calibration result did not match the expected contract.");
      }
      publishPlanUpdated(value.plan);
      setResult(value);
      setAttempt(null);
      setAnswers({});
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The calibration attempt could not be scored."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="calibration-workspace" aria-labelledby="calibration-heading">
      <header className="calibration-header">
        <div>
          <p className="eyebrow">Objective planning calibration</p>
          <h2 id="calibration-heading">Check what you can recognize without hints.</h2>
          <p>
            Four short single-choice questions sample your current priority gaps. Correct
            answers remain on the server until submission, and the result adjusts curriculum
            ordering conservatively rather than certifying job readiness.
          </p>
        </div>
        <div className="calibration-policy" aria-label="Calibration boundaries">
          <span>30-minute signed attempt</span>
          <span>Answers hidden until submission</span>
          <span>30% maximum readiness influence</span>
        </div>
      </header>

      {error !== null ? (
        <div className="error-banner" role="alert">
          <p>{error}</p>
        </div>
      ) : null}

      {!hasPlan ? (
        <div className="calibration-empty">
          <strong>Create your adaptive learning plan first.</strong>
          <p>
            Calibration is bound to the exact signed learner state and cannot run without an
            active browser-resumable plan.
          </p>
        </div>
      ) : null}

      {hasPlan && attempt === null && result === null ? (
        <div className="calibration-start">
          <div>
            <strong>Ready for a four-question calibration?</strong>
            <p>
              The engine selects competencies from your current largest planning gaps. It does
              not expose the answer key in the browser or attempt token.
            </p>
          </div>
          <button
            className="button button-primary"
            type="button"
            disabled={busy}
            onClick={() => void startAssessment()}
          >
            {busy ? "Preparing calibration…" : "Start calibration"}
          </button>
        </div>
      ) : null}

      {attempt !== null ? (
        <form className="calibration-form" onSubmit={submitAssessment}>
          <div className="calibration-attempt-meta">
            <span>Bank {attempt.bank_version}</span>
            <span>Expires {formatExpiry(attempt.expires_at)}</span>
            <span>
              {answeredCount}/{attempt.questions.length} answered
            </span>
          </div>

          <ol className="calibration-questions">
            {attempt.questions.map((question, index) => (
              <li key={question.id}>
                <fieldset>
                  <legend>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{question.competency_name}</strong>
                    <p>{question.prompt}</p>
                  </legend>
                  <div className="calibration-options">
                    {question.options.map((option) => (
                      <label key={option.id}>
                        <input
                          type="radio"
                          name={question.id}
                          value={option.id}
                          checked={answers[question.id] === option.id}
                          onChange={() =>
                            setAnswers((current) => ({
                              ...current,
                              [question.id]: option.id
                            }))
                          }
                        />
                        <span>{option.text}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              </li>
            ))}
          </ol>

          <div className="calibration-submit">
            <p>
              Submission is final for this attempt. Starting or updating another plan state
              invalidates this signed attempt.
            </p>
            <button
              className="button button-primary"
              type="submit"
              disabled={busy || answeredCount !== attempt.questions.length}
            >
              {busy ? "Scoring calibration…" : "Submit and recalibrate my plan"}
            </button>
          </div>
        </form>
      ) : null}

      {result !== null ? (
        <div className="calibration-result" role="status">
          <div className="calibration-score">
            <p className="step-label">Calibration result</p>
            <strong>{result.score_percent}%</strong>
            <span>
              {result.correct_count} of {result.total_count} correct · assessment coverage {" "}
              {result.plan.assessment_coverage_percent}%
            </span>
          </div>
          <div className="calibration-feedback">
            {result.feedback.map((item, index) => (
              <article className={item.correct ? "feedback-correct" : "feedback-review"} key={item.question_id}>
                <p>
                  Question {index + 1} · {item.correct ? "Correct" : "Review needed"}
                </p>
                <span>{item.explanation}</span>
              </article>
            ))}
          </div>
          <div className="calibration-result-actions">
            <p>
              Your active build missions were regenerated from the combined evidence and
              calibration signal. Evidence readiness remains visible separately.
            </p>
            <button
              className="button button-quiet"
              type="button"
              disabled={busy}
              onClick={() => void startAssessment()}
            >
              Start another calibration
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
