"use client";

import Link from "next/link";

import { useCareerApp } from "./app-provider";
import { Metric, NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

function readinessLabel(value: number): string {
  if (value >= 80) {
    return "Strong provisional readiness";
  }
  if (value >= 60) {
    return "Approaching role readiness";
  }
  if (value >= 35) {
    return "Material gaps remain";
  }
  return "Early role preparation";
}

export function ReadinessView() {
  const { plan } = useCareerApp();
  if (plan === null) {
    return <NoPlan />;
  }

  const weakest = [...plan.priority_competencies]
    .sort((left, right) => right.gap_percent - left.gap_percent)
    .slice(0, 5);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Readiness"
        title="Know what is proven—and what still blocks the role."
        description="Readiness is a planning signal built from provisional evidence and objective calibration. It is not an employment certificate and it should fall when new evidence contradicts earlier confidence."
        action={<Link className="button button-primary" href="/app/learn">Work the biggest gap</Link>}
      />

      <section className={styles.metrics}>
        <Metric label="Combined readiness" value={`${plan.readiness_percent}%`} note={readinessLabel(plan.readiness_percent)} />
        <Metric label="Evidence signal" value={`${plan.evidence_readiness_percent}%`} note={`${plan.evidence_history.length} evidence records retained`} />
        <Metric label="Calibration coverage" value={`${plan.assessment_coverage_percent}%`} note={`${plan.assessment_history.length} completed assessments`} />
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Largest remaining gaps</span>
          <h2>What would most improve credibility now</h2>
          <ul className={styles.competencyList}>
            {weakest.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    effective {competency.effective_percent}% · gap {competency.gap_percent}%
                    {competency.assessment_percent === null ? " · no objective calibration" : ""}
                  </small>
                  <span className={styles.progress}><span style={{ width: `${competency.effective_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.gap_percent}% gap</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Readiness interpretation</span>
          <h2>{readinessLabel(plan.readiness_percent)}</h2>
          <p>
            The platform currently knows about {plan.role.competencies.length} competencies for this
            role. It has objective assessment coverage for {plan.assessment_coverage_percent}% of the
            graph and {plan.evidence_history.length} learner-attested evidence records.
          </p>
          <div className={styles.readinessBand}>
            <div>
              <strong>Current active blocker</strong>
              <p>{plan.current_activity?.competency_name ?? "No active mission"}</p>
            </div>
            <span>{plan.priority_competencies[0]?.gap_percent ?? 0}%</span>
          </div>
          <p>
            A high number without recent, defensible work should not be trusted. Projects, calibration,
            and spaced review are deliberately separate signals.
          </p>
        </article>
      </section>
    </div>
  );
}
