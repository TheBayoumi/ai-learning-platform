"use client";

import Link from "next/link";

import { useCareerApp } from "./app-provider";
import { Metric, NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

export function ReadinessView() {
  const { plan } = useCareerApp();
  if (plan === null) {
    return <NoPlan />;
  }

  const weakest = [...plan.priority_competencies]
    .sort((left, right) => right.priority_gap_percent - left.priority_gap_percent)
    .slice(0, 5);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Readiness evidence gate"
        title="Readiness is not available until the evidence contract is satisfied."
        description="Career Atlas will not turn self-report, activity completion, chat fluency, or an unreviewed portfolio into a readiness score. This page shows what is known, what is only a planning signal, and which proof gates are still missing."
        action={<Link className="button button-primary" href="/app/learn">Work the next evidence gap</Link>}
      />

      <section className={styles.metrics}>
        <Metric label="Readiness conclusion" value="Locked" note={`Claim state · ${plan.claim_state}`} />
        <Metric label="Diagnostic signal" value={`${plan.diagnostic_signal_percent}%`} note="Prioritization signal only · not verified mastery" />
        <Metric label="Calibration coverage" value={`${plan.assessment_coverage_percent}%`} note={`${plan.assessment_history.length} completed calibration attempts`} />
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Largest current evidence priorities</span>
          <h2>What the engine should investigate next</h2>
          <ul className={styles.competencyList}>
            {weakest.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    diagnostic signal {competency.diagnostic_signal_percent}% · priority gap {competency.priority_gap_percent}%
                    {competency.assessment_percent === null ? " · no calibration yet" : ""}
                  </small>
                  <span className={styles.progress}><span style={{ width: `${competency.diagnostic_signal_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.priority_gap_percent}% gap</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Why readiness is locked</span>
          <h2>No verified readiness percentage exists yet.</h2>
          <p>
            The current engine can resolve a Target, prioritize work, record learner-attested evidence,
            and run bounded calibrations. Those capabilities are useful for planning, but they do not
            satisfy the original readiness contract.
          </p>
          <ul className={styles.criteria}>
            <li>Independent no-hint performance must be verified.</li>
            <li>Reasoning or explain-back evidence must be accepted deterministically.</li>
            <li>Delayed retention and transfer evidence must exist where applicable.</li>
            <li>Important work needs provenance, assistance disclosure, modification/debugging, and defense.</li>
            <li>Mandatory competency gaps and unresolved overlays must be evaluated against one exact RoleProfile version.</li>
            <li>The external practitioner/cohort validation gates must pass before the readiness claim can be promoted.</li>
          </ul>
          <p>
            Current Target: {plan.target.seniority} · {plan.target.labor_market} · {plan.target.timeline_weeks} weeks.
          </p>
        </article>
      </section>
    </div>
  );
}
