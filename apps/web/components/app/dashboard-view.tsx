"use client";

import Link from "next/link";

import { useCareerApp } from "./app-provider";
import { Metric, NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

function formatReview(value: string | null): string {
  if (value === null) {
    return "No review scheduled";
  }
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "Review date unavailable";
  }
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function DashboardView() {
  const { plan } = useCareerApp();
  if (plan === null) {
    return <NoPlan />;
  }

  const completion = plan.total_count === 0 ? 0 : Math.round((plan.completed_count / plan.total_count) * 100);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Dashboard"
        title={`Welcome back, ${plan.learner_name}.`}
        description={`Your ${plan.role.title} path is driven by evidence, calibration, and current capacity—not a fixed course sequence.`}
        action={<Link className="button button-primary" href="/app/learn">Continue learning</Link>}
      />

      <section className={styles.metrics} aria-label="Learning signals">
        <Metric label="Role readiness" value={`${plan.readiness_percent}%`} note="Combined provisional signal" />
        <Metric label="Evidence readiness" value={`${plan.evidence_readiness_percent}%`} note="Attested work and mastery signal" />
        <Metric label="Assessment coverage" value={`${plan.assessment_coverage_percent}%`} note="Competencies calibrated objectively" />
      </section>

      <section className={styles.grid2}>
        <article className={styles.activity}>
          <span className={styles.label}>Current mission</span>
          {plan.current_activity === null ? (
            <div>
              <h2>No active mission</h2>
              <p>Your current queue is complete. Replan or wait for a scheduled review.</p>
            </div>
          ) : (
            <>
              <div className={styles.activityMeta}>
                <span className={styles.pill}>{plan.current_activity.kind}</span>
                <span className={styles.pill}>{plan.current_activity.competency_name}</span>
                <span className={styles.pill}>{plan.current_activity.estimated_minutes} min</span>
              </div>
              <h2>{plan.current_activity.title}</h2>
              <p>{plan.current_activity.objective}</p>
              <ul className={styles.criteria}>
                {plan.current_activity.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
              </ul>
              <div className={styles.actions}>
                <Link className="button button-primary" href="/app/learn">Open mission</Link>
                <Link className="button button-quiet" href="/app/projects">Project evidence</Link>
              </div>
            </>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Priority gaps</span>
          <h2>What the engine is prioritizing now</h2>
          <ul className={styles.competencyList}>
            {plan.priority_competencies.slice(0, 6).map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>{competency.category}{competency.focused ? " · explicit focus" : ""}</small>
                  <span className={styles.progress}><span style={{ width: `${competency.effective_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.effective_percent}%</span>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className={styles.grid3}>
        <article className={styles.card}>
          <span className={styles.label}>Plan state</span>
          <h3>{plan.completed_count} of {plan.total_count} activities complete</h3>
          <div className={styles.progress}><span style={{ width: `${completion}%` }} /></div>
          <p>Revision {plan.plan_revision} · {plan.weekly_hours} hours/week.</p>
        </article>
        <article className={styles.card}>
          <span className={styles.label}>Evidence portfolio</span>
          <h3>{plan.evidence_history.length} accepted learner records</h3>
          <p>Use Projects to inspect what you submitted and what each record changed provisionally.</p>
        </article>
        <article className={styles.card}>
          <span className={styles.label}>Next evidence review</span>
          <h3>{formatReview(plan.next_review_at)}</h3>
          <p>Spaced reviews can pre-empt new build work when prior evidence becomes due.</p>
        </article>
      </section>
    </div>
  );
}
