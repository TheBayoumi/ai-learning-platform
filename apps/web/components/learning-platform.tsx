"use client";

import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  isPlanView,
  isRoleList,
  readPlatformError,
  type PlanView,
  type RoleView
} from "../lib/learning-contract";
import {
  PLAN_UPDATED_EVENT,
  publishPlanSaved,
  type PlanUpdatedDetail
} from "../lib/learning-events";
import { LEARNING_SESSION_STORAGE_KEY } from "../lib/learning-session";

type ApiAvailability = "available" | "unavailable" | "invalid-response";

interface LearningPlatformProps {
  readonly apiAvailability: ApiAvailability;
}

interface RequestOptions {
  readonly body?: unknown;
  readonly method?: "GET" | "POST";
}

async function platformRequest(
  path: string,
  options: RequestOptions = {}
): Promise<unknown> {
  const response = await fetch(`/api/platform/${path}`, {
    method: options.method ?? "GET",
    headers:
      options.body === undefined
        ? { accept: "application/json" }
        : {
            accept: "application/json",
            "content-type": "application/json"
          },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
    credentials: "same-origin"
  });
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new Error("The learning service returned an unreadable response.");
  }
  if (!response.ok) {
    throw new Error(readPlatformError(value));
  }
  return value;
}

function initialRatings(role: RoleView | undefined): Record<string, number> {
  if (role === undefined) {
    return {};
  }
  return Object.fromEntries(
    role.competencies.map((competency) => [competency.id, 0])
  );
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "No review scheduled";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) {
    return "Review date unavailable";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(parsed);
}

export function LearningPlatform({ apiAvailability }: LearningPlatformProps) {
  const [roles, setRoles] = useState<readonly RoleView[]>([]);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [learnerName, setLearnerName] = useState("");
  const [experienceSummary, setExperienceSummary] = useState("");
  const [weeklyHours, setWeeklyHours] = useState(8);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [reflection, setReflection] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [criteriaMet, setCriteriaMet] = useState<readonly string[]>([]);
  const [confidence, setConfidence] = useState(0);
  const [replanHours, setReplanHours] = useState(8);
  const [focusCompetencyIds, setFocusCompetencyIds] = useState<readonly string[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeRole = roles[0];

  const resetEvidenceForm = useCallback(() => {
    setReflection("");
    setEvidenceReference("");
    setCriteriaMet([]);
    setConfidence(0);
  }, []);

  const storePlan = useCallback(
  (nextPlan: PlanView) => {
    setPlan(nextPlan);
    setReplanHours(nextPlan.weekly_hours);
    setFocusCompetencyIds([...nextPlan.focus_competency_ids]);
    resetEvidenceForm();
    window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, nextPlan.state_token);
    publishPlanSaved();
  },
  [resetEvidenceForm]
);

  const loadPlatform = useCallback(async () => {
    try {
      const roleValue = await platformRequest("roles");
      if (!isRoleList(roleValue)) {
        throw new Error("The role catalog did not match the expected contract.");
      }
      setRoles(roleValue);
      setRatings((current) =>
        Object.keys(current).length === 0 ? initialRatings(roleValue[0]) : current
      );

      const token = window.localStorage.getItem(LEARNING_SESSION_STORAGE_KEY);
      if (token !== null) {
        const planValue = await platformRequest("plans/resume", {
          method: "POST",
          body: { state_token: token }
        });
        if (!isPlanView(planValue)) {
          throw new Error("The saved learning plan did not match the expected contract.");
        }
        storePlan(planValue);
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The learning platform could not be loaded."
      );
    } finally {
      setBusy(false);
    }
  }, [storePlan]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadPlatform();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [loadPlatform]);

  useEffect(() => {
    const handlePlanUpdated = (event: Event) => {
      if (!(event instanceof CustomEvent)) {
        return;
      }
      const detail = event.detail as PlanUpdatedDetail | undefined;
      if (detail !== undefined && isPlanView(detail.plan)) {
        storePlan(detail.plan);
      }
    };
    window.addEventListener(PLAN_UPDATED_EVENT, handlePlanUpdated);
    return () => window.removeEventListener(PLAN_UPDATED_EVENT, handlePlanUpdated);
  }, [storePlan]);



  const createPlan = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (activeRole === undefined) {
      setError("The target role is not available yet.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const value = await platformRequest("plans", {
        method: "POST",
        body: {
          learner_name: learnerName,
          target_role: activeRole.id,
          weekly_hours: weeklyHours,
          experience_summary: experienceSummary,
          ratings: activeRole.competencies.map((competency) => ({
            competency_id: competency.id,
            score: ratings[competency.id] ?? 0
          }))
        }
      });
      if (!isPlanView(value)) {
        throw new Error("The generated learning plan did not match the expected contract.");
      }
      storePlan(value);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The learning plan could not be generated."
      );
    } finally {
      setBusy(false);
    }
  };

  const completeCurrentActivity = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    if (plan?.current_activity === null || plan?.current_activity === undefined) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const value = await platformRequest("progress", {
        method: "POST",
        body: {
          state_token: plan.state_token,
          activity_id: plan.current_activity.id,
          reflection,
          evidence_reference: evidenceReference,
          criteria_met: criteriaMet,
          confidence
        }
      });
      if (!isPlanView(value)) {
        throw new Error("The updated learning plan did not match the expected contract.");
      }
      storePlan(value);
      resetEvidenceForm();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Evidence could not be recorded."
      );
    } finally {
      setBusy(false);
    }
  };

  const replanCurriculum = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (plan === null) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const value = await platformRequest("plans/replan", {
        method: "POST",
        body: {
          state_token: plan.state_token,
          weekly_hours: replanHours,
          focus_competency_ids: focusCompetencyIds
        }
      });
      if (!isPlanView(value)) {
        throw new Error("The replanned curriculum did not match the expected contract.");
      }
      storePlan(value);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The curriculum could not be replanned."
      );
    } finally {
      setBusy(false);
    }
  };

  const resetPlan = () => {
    window.localStorage.removeItem(LEARNING_SESSION_STORAGE_KEY);
    setPlan(null);
    resetEvidenceForm();
    setError(null);
  };

  const progressPercent = useMemo(() => {
    if (plan === null || plan.total_count === 0) {
      return 0;
    }
    return Math.round((plan.completed_count / plan.total_count) * 100);
  }, [plan]);

  const availabilityLabel = {
    available: "Learning service online",
    unavailable: "Learning service unavailable",
    "invalid-response": "Learning service contract mismatch"
  }[apiAvailability];

  return (
    <section className="learning-product" aria-labelledby="learning-product-heading">
      <div className="product-toolbar">
        <div>
          <p className="eyebrow">Career accelerator · adaptive evidence cycle</p>
          <h2 id="learning-product-heading">
            {plan === null ? "Build your personal path" : `Welcome back, ${plan.learner_name}`}
          </h2>
        </div>
        <div className="toolbar-actions">
          <span className={`service-state service-state-${apiAvailability}`} role="status">
            <span aria-hidden="true" />
            {availabilityLabel}
          </span>
          {plan !== null ? (
            <button className="button button-quiet" type="button" onClick={resetPlan}>
              Start again
            </button>
          ) : null}
        </div>
      </div>

      {error !== null ? (
        <div className="error-banner" role="alert">
          <p>{error}</p>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setBusy(true);
              setError(null);
              void loadPlatform();
            }}
          >
            Retry connection
          </button>
        </div>
      ) : null}

      {plan === null ? (
        <OnboardingForm
          role={activeRole}
          learnerName={learnerName}
          experienceSummary={experienceSummary}
          weeklyHours={weeklyHours}
          ratings={ratings}
          busy={busy}
          onLearnerNameChange={setLearnerName}
          onExperienceSummaryChange={setExperienceSummary}
          onWeeklyHoursChange={setWeeklyHours}
          onRatingChange={(competencyId, score) =>
            setRatings((current) => ({ ...current, [competencyId]: score }))
          }
          onSubmit={createPlan}
        />
      ) : (
        <Dashboard
          plan={plan}
          progressPercent={progressPercent}
          reflection={reflection}
          evidenceReference={evidenceReference}
          criteriaMet={criteriaMet}
          confidence={confidence}
          replanHours={replanHours}
          focusCompetencyIds={focusCompetencyIds}
          busy={busy}
          onReflectionChange={setReflection}
          onEvidenceReferenceChange={setEvidenceReference}
          onConfidenceChange={setConfidence}
          onCriterionToggle={(criterion, checked) =>
            setCriteriaMet((current) =>
              checked
                ? [...current, criterion]
                : current.filter((item) => item !== criterion)
            )
          }
          onReplanHoursChange={setReplanHours}
          onFocusToggle={(competencyId, checked) =>
            setFocusCompetencyIds((current) => {
              if (!checked) {
                return current.filter((item) => item !== competencyId);
              }
              if (current.includes(competencyId) || current.length >= 4) {
                return current;
              }
              return [...current, competencyId];
            })
          }
          onComplete={completeCurrentActivity}
          onReplan={replanCurriculum}
        />
      )}
    </section>
  );
}

interface OnboardingFormProps {
  readonly role: RoleView | undefined;
  readonly learnerName: string;
  readonly experienceSummary: string;
  readonly weeklyHours: number;
  readonly ratings: Readonly<Record<string, number>>;
  readonly busy: boolean;
  readonly onLearnerNameChange: (value: string) => void;
  readonly onExperienceSummaryChange: (value: string) => void;
  readonly onWeeklyHoursChange: (value: number) => void;
  readonly onRatingChange: (competencyId: string, score: number) => void;
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function OnboardingForm({
  role,
  learnerName,
  experienceSummary,
  weeklyHours,
  ratings,
  busy,
  onLearnerNameChange,
  onExperienceSummaryChange,
  onWeeklyHoursChange,
  onRatingChange,
  onSubmit
}: OnboardingFormProps) {
  return (
    <form className="onboarding-grid" onSubmit={onSubmit}>
      <section className="form-card form-card-primary">
        <p className="step-label">Step 01 · Direction</p>
        <h3>{role?.title ?? "Loading target role…"}</h3>
        <p className="muted-copy">
          {role?.summary ??
            "Connecting to the role catalog and competency engine."}
        </p>

        <label className="field-label" htmlFor="learner-name">
          Your name
        </label>
        <input
          id="learner-name"
          name="learner-name"
          type="text"
          autoComplete="name"
          minLength={2}
          maxLength={80}
          required
          value={learnerName}
          onChange={(event) => onLearnerNameChange(event.target.value)}
          placeholder="Mahmoud"
        />

        <label className="field-label" htmlFor="experience-summary">
          Current experience and transition goal
        </label>
        <textarea
          id="experience-summary"
          name="experience-summary"
          maxLength={600}
          rows={5}
          value={experienceSummary}
          onChange={(event) => onExperienceSummaryChange(event.target.value)}
          placeholder="Example: embedded software engineer moving into Python backend and AI systems."
        />

        <label className="field-label" htmlFor="weekly-hours">
          Weekly learning capacity: <strong>{weeklyHours} hours</strong>
        </label>
        <input
          id="weekly-hours"
          name="weekly-hours"
          type="range"
          min={2}
          max={20}
          step={1}
          value={weeklyHours}
          onChange={(event) => onWeeklyHoursChange(Number(event.target.value))}
        />
      </section>

      <section className="form-card competency-card">
        <p className="step-label">Step 02 · Diagnosis</p>
        <h3>Rate your current evidence</h3>
        <p className="muted-copy">
          Use 0 for no practical evidence and 4 for work you can independently defend.
        </p>
        <div className="rating-list">
          {role?.competencies.map((competency) => (
            <label className="rating-row" key={competency.id}>
              <span>
                <strong>{competency.name}</strong>
                <small>{competency.category}</small>
              </span>
              <select
                aria-label={`${competency.name} self-rating`}
                value={ratings[competency.id] ?? 0}
                onChange={(event) =>
                  onRatingChange(competency.id, Number(event.target.value))
                }
              >
                <option value={0}>0 · New</option>
                <option value={1}>1 · Aware</option>
                <option value={2}>2 · Guided</option>
                <option value={3}>3 · Independent</option>
                <option value={4}>4 · Defensible</option>
              </select>
            </label>
          ))}
        </div>
        <button
          className="button button-primary"
          type="submit"
          disabled={busy || role === undefined}
        >
          {busy ? "Building your plan…" : "Generate my learning path"}
        </button>
        <p className="privacy-note">
          This slice stores a signed learning session in this browser. It does not create an
          account or upload a private résumé.
        </p>
      </section>
    </form>
  );
}

interface DashboardProps {
  readonly plan: PlanView;
  readonly progressPercent: number;
  readonly reflection: string;
  readonly evidenceReference: string;
  readonly criteriaMet: readonly string[];
  readonly confidence: number;
  readonly replanHours: number;
  readonly focusCompetencyIds: readonly string[];
  readonly busy: boolean;
  readonly onReflectionChange: (value: string) => void;
  readonly onEvidenceReferenceChange: (value: string) => void;
  readonly onConfidenceChange: (value: number) => void;
  readonly onCriterionToggle: (criterion: string, checked: boolean) => void;
  readonly onReplanHoursChange: (value: number) => void;
  readonly onFocusToggle: (competencyId: string, checked: boolean) => void;
  readonly onComplete: (event: FormEvent<HTMLFormElement>) => void;
  readonly onReplan: (event: FormEvent<HTMLFormElement>) => void;
}

function Dashboard({
  plan,
  progressPercent,
  reflection,
  evidenceReference,
  criteriaMet,
  confidence,
  replanHours,
  focusCompetencyIds,
  busy,
  onReflectionChange,
  onEvidenceReferenceChange,
  onConfidenceChange,
  onCriterionToggle,
  onReplanHoursChange,
  onFocusToggle,
  onComplete,
  onReplan
}: DashboardProps) {
  return (
    <div className="dashboard-grid">
      <aside className="dashboard-summary">
        <div className="readiness-card">
          <p className="step-label">Provisional readiness signal</p>
          <div className="readiness-value">
            <strong>{plan.readiness_percent}%</strong>
            <span>self-reported evidence estimate</span>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Plan completion"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
          >
            <span style={{ width: `${progressPercent}%` }} />
          </div>
          <p className="progress-copy">
            {plan.completed_count} of {plan.total_count} active activities complete · revision {plan.plan_revision}
          </p>
        </div>

        <div className="priority-panel">
          <p className="step-label">Priority gaps</p>
          <ul>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <div>
                  <strong>
                    {competency.name}
                    {competency.focused ? <em>Focus</em> : null}
                  </strong>
                  <small>{competency.category}</small>
                </div>
                <span>{competency.mastery_percent}%</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="review-panel">
          <p className="step-label">Evidence rhythm</p>
          <strong>{formatDateTime(plan.next_review_at)}</strong>
          <span>{plan.evidence_history.length} recent evidence records retained</span>
        </div>

        <details className="replan-panel">
          <summary>Rebuild active curriculum</summary>
          <form onSubmit={onReplan}>
            <label className="field-label" htmlFor="replan-hours">
              Weekly capacity: <strong>{replanHours} hours</strong>
            </label>
            <input
              id="replan-hours"
              type="range"
              min={2}
              max={20}
              value={replanHours}
              onChange={(event) => onReplanHoursChange(Number(event.target.value))}
            />
            <fieldset className="focus-list">
              <legend>Optional focus areas · up to four</legend>
              {plan.role.competencies.map((competency) => (
                <label key={competency.id}>
                  <input
                    type="checkbox"
                    checked={focusCompetencyIds.includes(competency.id)}
                    disabled={
                      !focusCompetencyIds.includes(competency.id) &&
                      focusCompetencyIds.length >= 4
                    }
                    onChange={(event) =>
                      onFocusToggle(competency.id, event.target.checked)
                    }
                  />
                  <span>{competency.name}</span>
                </label>
              ))}
            </fieldset>
            <button className="button button-quiet" type="submit" disabled={busy}>
              {busy ? "Replanning…" : "Rebuild my active plan"}
            </button>
          </form>
        </details>
      </aside>

      <section className="activity-panel">
        {plan.current_activity === null ? (
          <div className="completion-state">
            <p className="step-label">No activity available now</p>
            <h3>Your active work is complete or waiting for review.</h3>
            <p>
              Use the curriculum controls to generate another focused cycle, or return when the
              next spaced review becomes available.
            </p>
            <strong>{formatDateTime(plan.next_review_at)}</strong>
          </div>
        ) : (
          <>
            <div className="activity-heading">
              <div>
                <p className="step-label">
                  {plan.current_activity.kind === "review" ? "Spaced review" : "Current mission"}
                  {" · "}
                  {plan.current_activity.competency_name}
                </p>
                <h3>{plan.current_activity.title}</h3>
              </div>
              <span>{plan.current_activity.estimated_minutes} min</span>
            </div>
            <p className="activity-objective">{plan.current_activity.objective}</p>
            <p className="activity-rationale">{plan.current_activity.rationale}</p>

            <div className="deliverable-box">
              <p>Required deliverable</p>
              <strong>{plan.current_activity.deliverable}</strong>
            </div>

            <form className="completion-form" onSubmit={onComplete}>
              <fieldset className="criteria-checklist">
                <legend className="step-label">Acceptance criteria met</legend>
                {plan.current_activity.acceptance_criteria.map((criterion) => (
                  <label key={criterion}>
                    <input
                      type="checkbox"
                      checked={criteriaMet.includes(criterion)}
                      onChange={(event) =>
                        onCriterionToggle(criterion, event.target.checked)
                      }
                    />
                    <span>{criterion}</span>
                  </label>
                ))}
              </fieldset>

              <label className="field-label" htmlFor="evidence-reference">
                Evidence reference
              </label>
              <input
                id="evidence-reference"
                type="text"
                maxLength={500}
                value={evidenceReference}
                onChange={(event) => onEvidenceReferenceChange(event.target.value)}
                placeholder="Repository, pull request, document, local artifact name, or concise locator"
              />

              <label className="field-label" htmlFor="activity-confidence">
                Confidence reproducing this independently
              </label>
              <select
                id="activity-confidence"
                value={confidence}
                onChange={(event) => onConfidenceChange(Number(event.target.value))}
              >
                <option value={0}>0 · Cannot reproduce yet</option>
                <option value={1}>1 · Heavy support required</option>
                <option value={2}>2 · Some guidance required</option>
                <option value={3}>3 · Independent with references</option>
                <option value={4}>4 · Independent and defensible</option>
              </select>

              <label className="field-label" htmlFor="activity-reflection">
                Evidence reflection
              </label>
              <textarea
                id="activity-reflection"
                rows={4}
                maxLength={1_000}
                value={reflection}
                onChange={(event) => onReflectionChange(event.target.value)}
                placeholder="What did you build, what evidence supports it, what failed, and what would you improve?"
              />
              <button className="button button-primary" type="submit" disabled={busy}>
                {busy ? "Recording evidence…" : "Record evidence and schedule review"}
              </button>
              <p className="privacy-note">
                Mastery changes are provisional and based on your attestation. They are not an
                external assessment or employer certification.
              </p>
            </form>

            {plan.evidence_history.length > 0 ? (
              <section className="evidence-history" aria-labelledby="evidence-history-heading">
                <p className="step-label" id="evidence-history-heading">Recent evidence</p>
                <ol>
                  {[...plan.evidence_history].reverse().slice(0, 4).map((evidence) => (
                    <li key={`${evidence.activity_id}-${evidence.submitted_at}`}>
                      <div>
                        <strong>{evidence.competency_name}</strong>
                        <span>{evidence.title}</span>
                      </div>
                      <small>
                        +{evidence.provisional_mastery_delta} provisional · confidence {evidence.confidence}/4 · review {formatDateTime(evidence.next_review_at)}
                      </small>
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}
