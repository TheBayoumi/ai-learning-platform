"use client";

import Link from "next/link";

import { useCareerApp } from "./app-provider";
import { NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Unknown date"
    : new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(date);
}

export function ProjectsView() {
  const { plan } = useCareerApp();
  if (plan === null) {
    return <NoPlan />;
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Projects & evidence"
        title="The portfolio is the proof layer."
        description="Career Atlas does not count a clicked lesson as readiness. This view is built around work you can point to, explain, and revisit."
        action={<Link className="button button-primary" href="/app/learn">Open current mission</Link>}
      />

      <section className={styles.grid2}>
        <article className={styles.activity}>
          <span className={styles.label}>Active project / mission</span>
          {plan.current_activity === null ? (
            <>
              <h2>No active mission</h2>
              <p>Replan the roadmap or wait for a scheduled review.</p>
            </>
          ) : (
            <>
              <div className={styles.activityMeta}>
                <span className={styles.pill}>{plan.current_activity.kind}</span>
                <span className={styles.pill}>{plan.current_activity.competency_name}</span>
              </div>
              <h2>{plan.current_activity.title}</h2>
              <p>{plan.current_activity.deliverable}</p>
              <ul className={styles.criteria}>
                {plan.current_activity.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
              </ul>
            </>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Evidence portfolio</span>
          <h2>{plan.evidence_history.length} recorded evidence items</h2>
          <p>
            Records are learner-attested and provisional. Objective calibration and later reviews can
            strengthen or challenge the mastery signal.
          </p>
          {plan.evidence_history.length === 0 ? (
            <p>No evidence has been recorded yet. Complete the first mission with a defensible deliverable.</p>
          ) : (
            <ul className={styles.timeline}>
              {[...plan.evidence_history].reverse().map((record) => (
                <li key={`${record.activity_id}-${record.submitted_at}`}>
                  <time dateTime={record.submitted_at}>{formatDate(record.submitted_at)}</time>
                  <div>
                    <strong>{record.title}</strong>
                    <p>
                      {record.competency_name} · +{record.provisional_mastery_delta} provisional mastery · confidence {record.confidence}/4
                    </p>
                    {record.evidence_reference ? <p>Evidence: {record.evidence_reference}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </div>
  );
}
