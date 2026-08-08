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

  const evidenceCounts = plan.competency_evidence.reduce(
    (counts, item) => ({ ...counts, [item.status]: counts[item.status] + 1 }),
    { unverified: 0, partial: 0, independent: 0 }
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Readiness evidence gate"
        title="Readiness stays locked while evidence quality is built explicitly."
        description="Career Atlas now tracks authoritative competency evidence separately from self-report, activity completion, and calibration. Independent evidence is still not role readiness: retention, transfer, provenance, realistic work, overlay coverage, and external validation remain required."
        action={<Link className="button button-primary" href="/app/learn">Work the next evidence gap</Link>}
      />

      <section className={styles.metrics}>
        <Metric label="Readiness conclusion" value="Locked" note={`Claim state · ${plan.claim_state}`} />
        <Metric label="Independent evidence" value={`${evidenceCounts.independent}`} note={`${evidenceCounts.partial} partial · ${evidenceCounts.unverified} unverified competencies`} />
        <Metric label="Calibration coverage" value={`${plan.assessment_coverage_percent}%`} note="Diagnostic coverage only · not authoritative competency evidence" />
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Competency evidence state</span>
          <h2>What has actually passed a trusted evidence transition</h2>
          <ul className={styles.competencyList}>
            {plan.priority_competencies.map((competency) => (
              <li key={competency.id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.name}</strong>
                  <small>
                    evidence {competency.evidence_status} · diagnostic priority gap {competency.priority_gap_percent}%
                  </small>
                  <span className={styles.progress}><span style={{ width: `${competency.diagnostic_signal_percent}%` }} /></span>
                </span>
                <span className={styles.score}>{competency.evidence_status}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Why readiness is still locked</span>
          <h2>Independent evidence is necessary, but not sufficient.</h2>
          <ul className={styles.criteria}>
            <li>Learner-attested work remains unverified until a trusted evaluator accepts it.</li>
            <li>Independent status requires no-hint performance, no answer-level assistance, and verified reasoning.</li>
            <li>Retention-candidate review is a scheduled future check, not proof of retention.</li>
            <li>Transfer work, provenance, modification/debugging, defense, and realistic simulations still need later DoD slices.</li>
            <li>Mandatory gaps and active/unresolved overlays must eventually be evaluated against one exact RoleProfile version.</li>
            <li>Formal practitioner/cohort validation gates remain external and cannot be inferred from engineering implementation.</li>
          </ul>
        </article>
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Active misconceptions</span>
          <h2>{plan.active_misconceptions.length} trusted observations need attention</h2>
          {plan.active_misconceptions.length === 0 ? (
            <p>No trusted evaluator misconception record is active.</p>
          ) : (
            <ul className={styles.criteria}>
              {plan.active_misconceptions.map((item) => (
                <li key={item.misconception_id}>{item.competency_id} · {item.code}</li>
              ))}
            </ul>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Evidence follow-up state</span>
          <h2>{plan.review_state.length} scheduled evidence checks</h2>
          {plan.review_state.length === 0 ? (
            <p>No trusted-evidence follow-up is scheduled yet.</p>
          ) : (
            <ul className={styles.timeline}>
              {plan.review_state.map((item) => (
                <li key={`${item.competency_id}-${item.source_evidence_id}`}>
                  <time dateTime={item.due_at}>{new Date(item.due_at).toLocaleDateString()}</time>
                  <div>
                    <strong>{item.competency_id} · {item.stage.replaceAll("_", " ")}</strong>
                    <p>{item.reason}</p>
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
