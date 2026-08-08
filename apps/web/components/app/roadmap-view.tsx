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
        title={`${plan.role.title} planning map`}
        description="This is a work-priority projection against the resolved Target—not a mastery map. Self-report, learner-attested work, calibration, focus, reviews, and capacity can change the sequence while readiness stays validation-locked."
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Current planning priorities</span>
          <ul className={styles.competencyList}>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    {competency.category} · priority gap {competency.priority_gap_percent}%
                    {competency.assessment_percent === null ? " · not calibrated" : ` · calibration ${competency.assessment_percent}%`}
                  </small>
                  <span className={styles.progress}><span style={{ width: `${competency.diagnostic_signal_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.diagnostic_signal_percent}% signal</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.formCard}>
          <span className={styles.label}>Replan controls</span>
          <h2>Change constraints and priorities, not evidence claims.</h2>
          <p>
            Replanning regenerates active build work while preserving recorded work, calibration history,
            and pending spaced reviews. It cannot promote mastery or readiness.
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
