"use client";

import { type FormEvent, useState } from "react";

import { replan } from "../../lib/platform-client";
import { useCareerApp } from "./app-provider";
import { NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

export function RoadmapView() {
  const { plan, commitPlan } = useCareerApp();
  const [weeklyHours, setWeeklyHours] = useState(plan?.weekly_hours ?? 8);
  const [focus, setFocus] = useState<readonly string[]>(plan?.focus_competency_ids ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (plan === null) {
    return <NoPlan />;
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const next = await replan({
        state_token: plan.state_token,
        weekly_hours: weeklyHours,
        focus_competency_ids: focus
      });
      commitPlan(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The roadmap could not be replanned.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Roadmap"
        title={`${plan.role.title} competency map`}
        description="The role graph is stable enough to define the work. Your order through it is not: evidence, assessment, focus, reviews, and capacity continuously change the active sequence."
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Current competency state</span>
          <ul className={styles.competencyList}>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    {competency.category} · gap {competency.gap_percent}%
                    {competency.assessment_percent === null ? " · not calibrated" : ` · assessment ${competency.assessment_percent}%`}
                  </small>
                  <span className={styles.progress}><span style={{ width: `${competency.effective_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.effective_percent}%</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.formCard}>
          <span className={styles.label}>Replan controls</span>
          <h2>Change constraints, not fake progress.</h2>
          <p>
            Replanning regenerates active build work while preserving completed evidence, assessment history,
            and pending spaced reviews.
          </p>
          <form className={styles.form} onSubmit={submit}>
            <div className={styles.field}>
              <label htmlFor="roadmap-hours">Weekly capacity · {weeklyHours} hours</label>
              <input
                id="roadmap-hours"
                type="range"
                min={2}
                max={40}
                step={1}
                value={weeklyHours}
                onChange={(event) => setWeeklyHours(Number(event.target.value))}
              />
            </div>
            <div className={styles.field}>
              <label>Optional focus · choose up to 4 competencies</label>
              <div className={styles.checks}>
                {plan.role.competencies.map((competency) => (
                  <label className={styles.check} key={competency.id}>
                    <input
                      type="checkbox"
                      checked={focus.includes(competency.id)}
                      onChange={(event) =>
                        setFocus((current) => {
                          if (!event.target.checked) {
                            return current.filter((item) => item !== competency.id);
                          }
                          if (current.includes(competency.id) || current.length >= 4) {
                            return current;
                          }
                          return [...current, competency.id];
                        })
                      }
                    />
                    <span>{competency.name}</span>
                  </label>
                ))}
              </div>
            </div>
            <button className="button button-primary" disabled={busy} type="submit">
              {busy ? "Rebuilding roadmap…" : "Rebuild active roadmap"}
            </button>
          </form>
        </article>
      </section>
    </div>
  );
}
