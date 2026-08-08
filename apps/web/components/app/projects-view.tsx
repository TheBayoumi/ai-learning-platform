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
        title="Every artifact starts as an evidence candidate—not proof."
        description="Career Atlas now preserves source, disposition, independence, assistance, and reasoning state for recorded work. Learner attestation stays unverified until a separate trusted evaluator transition accepts it; provenance, retention, transfer, modification/debugging, defense, and realistic-work gates remain later requirements."
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
          <span className={styles.label}>Evidence candidate history</span>
          <h2>{plan.evidence_history.length} recorded items</h2>
          <p>
            A record can change planning priority, but only a trusted server-side evaluation can move
            the matching competency to partial or independent evidence state.
          </p>
          {plan.evidence_history.length === 0 ? (
            <p>No work has been recorded yet. Complete the first mission with a defensible deliverable.</p>
          ) : (
            <ul className={styles.timeline}>
              {[...plan.evidence_history].reverse().map((record) => (
                <li key={record.evidence_id}>
                  <time dateTime={record.submitted_at}>{formatDate(record.submitted_at)}</time>
                  <div>
                    <strong>{record.title}</strong>
                    <p>
                      {record.competency_name} · {record.source.replaceAll("_", " ")} · {record.disposition} · {record.independence}
                    </p>
                    <p>
                      assistance {record.assistance} · reasoning {record.reasoning.replaceAll("_", " ")} · +{record.planning_signal_delta} planning signal
                    </p>
                    {record.evidence_reference ? <p>Reference: {record.evidence_reference}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      <section className={styles.card}>
        <span className={styles.label}>Trusted evaluator history</span>
        <h2>{plan.evidence_evaluations.length} immutable evaluation records</h2>
        {plan.evidence_evaluations.length === 0 ? (
          <p>No trusted evaluator verdict has been committed yet.</p>
        ) : (
          <ul className={styles.timeline}>
            {[...plan.evidence_evaluations].reverse().map((evaluation) => (
              <li key={evaluation.evaluation_id}>
                <time dateTime={evaluation.occurred_at}>{formatDate(evaluation.occurred_at)}</time>
                <div>
                  <strong>{evaluation.competency_id} · {evaluation.disposition}</strong>
                  <p>
                    {evaluation.independence} · assistance {evaluation.assistance} · reasoning {evaluation.reasoning} · evaluator confidence {evaluation.confidence}%
                  </p>
                  <p>Rubric {evaluation.rubric_version} · evaluator {evaluation.evaluator_id}@{evaluation.evaluator_version}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
