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

  const activeVersion = plan.active_plan_version;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Roadmap"
        title={`${plan.role.title} planning map`}
        description="This is a deterministic work-priority projection against the exact Target and RoleProfile version. Authoritative evidence and prerequisites decide what is eligible; self-report and calibration can only order unresolved work."
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Active immutable plan</span>
          <h2>Revision {activeVersion.revision} · {activeVersion.trigger.replaceAll("_", " ")}</h2>
          <p>
            Plan <code>{activeVersion.plan_version_id}</code> is bound to role {activeVersion.role_version},
            graph {activeVersion.graph_version}, and evidence policy {activeVersion.evidence_policy_version}.
          </p>
          <p>{activeVersion.delta.reason}</p>
          <small>
            {activeVersion.delta.added_activity_ids.length} added · {activeVersion.delta.removed_activity_ids.length} removed · {activeVersion.delta.retained_activity_ids.length} retained
          </small>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Current evidence-aware priorities</span>
          <ul className={styles.competencyList}>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    {competency.category} · evidence {competency.evidence_status} · authoritative gap {competency.authoritative_gap_percent}%
                    {competency.assessment_percent === null ? " · not calibrated" : ` · calibration ${competency.assessment_percent}%`}
                  </small>
                  {competency.blocked_by.length > 0 ? (
                    <small>Blocked by independent evidence for: {competency.blocked_by.join(", ")}</small>
                  ) : null}
                  {competency.active_misconception_codes.length > 0 ? (
                    <small>Active misconceptions: {competency.active_misconception_codes.join(", ")}</small>
                  ) : null}
                  <small>{competency.priority_reason}</small>
                  <span className={styles.progress}><span style={{ width: `${competency.diagnostic_signal_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.diagnostic_signal_percent}% diagnostic signal</span>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Dependency contract</span>
          <h2>Prerequisites are evidence gates, not suggestions.</h2>
          <p>
            A downstream build is not scheduled until every prerequisite reaches independent evidence.
            High self-ratings, quiz scores, focus selections, or learner-attested completion cannot bypass that gate.
          </p>
          <small>
            Target fingerprint {activeVersion.target_fingerprint} · {activeVersion.priorities.length} competency decisions recorded
          </small>
        </article>

        <article className={styles.formCard}>
          <span className={styles.label}>Replan controls</span>
          <h2>Change constraints and priorities, not evidence claims.</h2>
          <p>
            Replanning creates a new immutable plan version while preserving evidence, prior versions,
            calibration history, and pending reviews. It cannot promote mastery or readiness.
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
              {busy ? "Rebuilding roadmap…" : "Create next plan version"}
            </button>
          </form>
        </article>
      </section>
    </div>
  );
}
