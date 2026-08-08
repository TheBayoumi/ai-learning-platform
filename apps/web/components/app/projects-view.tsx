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
        eyebrow="Projects & recorded work"
        title="A submitted artifact is a lead for verification—not proof by itself."
        description="This view records learner-attested work so the engine can schedule stronger checks later. Provenance, assistance, modification/debugging, defense, no-hint, retention, and transfer gates are still required before work can contribute to verified mastery or readiness."
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
          <span className={styles.label}>Learner-attested work history</span>
          <h2>{plan.evidence_history.length} recorded items</h2>
          <p>
            These records may change what the platform asks you to prove next. They do not increase
            verified mastery or role readiness by themselves.
          </p>
          {plan.evidence_history.length === 0 ? (
            <p>No work has been recorded yet. Complete the first mission with a defensible deliverable.</p>
          ) : (
            <ul className={styles.timeline}>
              {[...plan.evidence_history].reverse().map((record) => (
                <li key={`${record.activity_id}-${record.submitted_at}`}>
                  <time dateTime={record.submitted_at}>{formatDate(record.submitted_at)}</time>
                  <div>
                    <strong>{record.title}</strong>
                    <p>
                      {record.competency_name} · +{record.planning_signal_delta} planning signal · self-reported confidence {record.confidence}/4
                    </p>
                    {record.evidence_reference ? <p>Reference: {record.evidence_reference}</p> : null}
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
