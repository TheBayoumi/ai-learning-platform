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

const SESSION_STORAGE_KEY = "ai-career-learning-plan-v1";

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

export function LearningPlatform({ apiAvailability }: LearningPlatformProps) {
  const [roles, setRoles] = useState<readonly RoleView[]>([]);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [learnerName, setLearnerName] = useState("");
  const [experienceSummary, setExperienceSummary] = useState("");
  const [weeklyHours, setWeeklyHours] = useState(8);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [reflection, setReflection] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeRole = roles[0];

  const storePlan = useCallback((nextPlan: PlanView) => {
    setPlan(nextPlan);
    window.localStorage.setItem(SESSION_STORAGE_KEY, nextPlan.state_token);
  }, []);

  const loadPlatform = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const roleValue = await platformRequest("roles");
      if (!isRoleList(roleValue)) {
        throw new Error("The role catalog did not match the expected contract.");
      }
      setRoles(roleValue);
      setRatings((current) =>
        Object.keys(current).length === 0 ? initialRatings(roleValue[0]) : current
      );

      const token = window.localStorage.getItem(SESSION_STORAGE_KEY);
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
    void loadPlatform();
  }, [loadPlatform]);

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
          reflection
        }
      });
      if (!isPlanView(value)) {
        throw new Error("The updated learning plan did not match the expected contract.");
      }
      storePlan(value);
      setReflection("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Progress could not be recorded."
      );
    } finally {
      setBusy(false);
    }
  };

  const resetPlan = () => {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    setPlan(null);
    setReflection("");
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
          <p className="eyebrow">Career accelerator · first live track</p>
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
          <button className="text-button" type="button" onClick={() => void loadPlatform()}>
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
          busy={busy}
          onReflectionChange={setReflection}
          onComplete={completeCurrentActivity}
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
  readonly busy: boolean;
  readonly onReflectionChange: (value: string) => void;
  readonly onComplete: (event: FormEvent<HTMLFormElement>) => void;
}

function Dashboard({
  plan,
  progressPercent,
  reflection,
  busy,
  onReflectionChange,
  onComplete
}: DashboardProps) {
  return (
    <div className="dashboard-grid">
      <aside className="dashboard-summary">
        <div className="readiness-card">
          <p className="step-label">Role readiness signal</p>
          <div className="readiness-value">
            <strong>{plan.readiness_percent}%</strong>
            <span>current evidence estimate</span>
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
            {plan.completed_count} of {plan.total_count} generated activities complete
          </p>
        </div>

        <div className="priority-panel">
          <p className="step-label">Priority gaps</p>
          <ul>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <div>
                  <strong>{competency.name}</strong>
                  <small>{competency.category}</small>
                </div>
                <span>{competency.mastery_percent}%</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <section className="activity-panel">
        {plan.current_activity === null ? (
          <div className="completion-state">
            <p className="step-label">Plan complete</p>
            <h3>You completed this generated evidence cycle.</h3>
            <p>
              Start a new diagnosis after adding the completed artifacts to your portfolio
              and updating ratings based on evidence—not confidence alone.
            </p>
          </div>
        ) : (
          <>
            <div className="activity-heading">
              <div>
                <p className="step-label">Current mission · {plan.current_activity.competency_name}</p>
                <h3>{plan.current_activity.title}</h3>
              </div>
              <span>{plan.current_activity.estimated_minutes} min</span>
            </div>
            <p className="activity-objective">{plan.current_activity.objective}</p>

            <div className="deliverable-box">
              <p>Required deliverable</p>
              <strong>{plan.current_activity.deliverable}</strong>
            </div>

            <div className="criteria-block">
              <p className="step-label">Acceptance criteria</p>
              <ul>
                {plan.current_activity.acceptance_criteria.map((criterion) => (
                  <li key={criterion}>{criterion}</li>
                ))}
              </ul>
            </div>

            <form className="completion-form" onSubmit={onComplete}>
              <label className="field-label" htmlFor="activity-reflection">
                Evidence reflection
              </label>
              <textarea
                id="activity-reflection"
                rows={4}
                maxLength={1_000}
                value={reflection}
                onChange={(event) => onReflectionChange(event.target.value)}
                placeholder="What did you build, what evidence proves it, and what would you improve?"
              />
              <button className="button button-primary" type="submit" disabled={busy}>
                {busy ? "Updating mastery…" : "Mark evidence cycle complete"}
              </button>
            </form>
          </>
        )}
      </section>
    </div>
  );
}
