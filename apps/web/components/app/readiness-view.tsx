"use client";

import Link from "next/link";

import { useCareerApp } from "./app-provider";
import { Metric, NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

function label(value: string) {
  return value.replaceAll("_", " ").replaceAll(":", " · ");
}

export function ReadinessView() {
  const { plan } = useCareerApp();
  if (plan === null) {
    return <NoPlan />;
  }

  const readiness = plan.readiness_projection;
  if (readiness === null || readiness === undefined) {
    return (
      <div className={styles.page}>
        <PageHeader
          eyebrow="Readiness evidence gate"
          title="Readiness projection is unavailable for this legacy state."
          description="Resume or replan this learner state to project exact mandatory evidence, retention, transfer, provenance, overlay, and validation blockers. No readiness claim is inferred while that projection is absent."
          action={<Link className="button button-primary" href="/app/learn">Resume learning</Link>}
        />
      </div>
    );
  }

  const completeCount = readiness.competencies.filter((item) => item.engineering_complete).length;
  const gapCount = readiness.mandatory_gap_ids.length;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Readiness evidence gate"
        title="Exact role evidence is projected without turning it into a hiring score."
        description={`This projection is bound to ${readiness.role_id} ${readiness.role_version} / ${readiness.graph_version}. Every mandatory competency is evaluated independently from trusted evidence, delayed retention, unseen transfer, verified work provenance, disputes, and misconceptions. External practitioner validation remains a separate gate.`}
        action={<Link className="button button-primary" href="/app/learn">Work the next mandatory gap</Link>}
      />

      <section className={styles.metrics}>
        <Metric
          label="Public readiness claim"
          value="Locked"
          note={`${label(readiness.claim_state)} · external approval required`}
        />
        <Metric
          label="Engineering evidence"
          value={readiness.engineering_evidence_complete ? "Complete" : `${gapCount} gaps`}
          note={`${completeCount}/${readiness.mandatory_competency_ids.length} mandatory competencies complete`}
        />
        <Metric
          label="Profile binding"
          value={readiness.role_version}
          note={`${readiness.graph_version} · ${readiness.evidence_policy_version}`}
        />
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Mandatory competency blockers</span>
          <h2>Strong evidence in one area cannot compensate for another required gap.</h2>
          <ul className={styles.competencyList}>
            {readiness.competencies.map((competency) => (
              <li key={competency.competency_id}>
                <span className={styles.itemTitle}>
                  <strong>{competency.competency_name}</strong>
                  <small>
                    evidence {competency.evidence_status} · proof {competency.satisfied_proof_classes.length}/4 · verified work {competency.verified_work_evidence_ids.length}
                  </small>
                  {competency.blocker_codes.length > 0 ? (
                    <small>{competency.blocker_codes.map(label).join(" · ")}</small>
                  ) : (
                    <small>Independent, retained, transferred, provenance-verified evidence complete.</small>
                  )}
                </span>
                <span className={styles.score}>
                  {competency.engineering_complete ? "complete" : "blocked"}
                </span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Claim boundary</span>
          <h2>Engineering completeness never self-promotes to job readiness.</h2>
          <ul className={styles.criteria}>
            <li>Claim state: {label(readiness.claim_state)}.</li>
            <li>RoleProfile validation: {readiness.role_validation_state}.</li>
            <li>Target validation: {readiness.target_validation_state}.</li>
            <li>External human/practitioner approval remains required.</li>
            <li>Self-report, calibration score, chat fluency, completion, and unreviewed work are excluded from readiness authority.</li>
            <li>No percentage is emitted because mandatory evidence classes are non-compensatory.</li>
          </ul>
        </article>
      </section>

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Target overlays and exclusions</span>
          <h2>{readiness.unresolved_overlay_deltas.length} overlay deltas remain unresolved</h2>
          <ul className={styles.criteria}>
            {readiness.active_overlays.length === 0 ? (
              <li>No active overlays were recorded.</li>
            ) : (
              readiness.active_overlays.map((item) => <li key={item}>{label(item)}</li>)
            )}
            {readiness.exclusions.map((item) => <li key={`exclusion-${item}`}>Excluded · {item}</li>)}
          </ul>
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Disputes and uncertainty</span>
          <h2>Unknowns stay visible instead of becoming optimistic defaults.</h2>
          <ul className={styles.criteria}>
            {readiness.disputed_evidence_ids.map((item) => (
              <li key={item}>Disputed evidence · {item}</li>
            ))}
            {readiness.stale_evidence_ids.map((item) => (
              <li key={`stale-${item}`}>Stale evidence · {item}</li>
            ))}
            {readiness.uncertainties.map((item) => (
              <li key={item}>{label(item)}</li>
            ))}
          </ul>
        </article>
      </section>
    </div>
  );
}
