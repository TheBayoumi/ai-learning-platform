import Link from "next/link";

import { resolveRuntimeApiAvailability } from "../server/health/runtime-health";
import styles from "./landing.module.css";

export const dynamic = "force-dynamic";
export const preferredRegion = "pdx1";

const tracks = [
  [
    "Junior Python Backend Engineer",
    "APIs, PostgreSQL, testing, delivery, debugging, and engineering communication."
  ],
  [
    "AI Application Engineer",
    "LLM applications, RAG, evaluation, backend integration, safety, and observability."
  ],
  [
    "Data Engineer",
    "Data models, pipelines, PostgreSQL, data quality, delivery, and operational reliability."
  ]
] as const;

const steps = [
  ["01", "Resolve the Target", "Bind the plan to a role version, seniority, labor market, timeline, geography, and explicit overlays."],
  ["02", "Rate your current evidence", "Use self-report only to decide where diagnosis and stronger evidence should start."],
  ["03", "Build and verify proof", "Work through learner-specific missions, calibrations, reviews, and progressively stronger evidence checks."],
  ["04", "Unlock readiness only from evidence", "Keep readiness locked until independent performance, retention, transfer, provenance, and realistic-work gates support it."]
] as const;

export default async function HomePage() {
  const apiAvailability = await resolveRuntimeApiAvailability();
  const availabilityLabel = {
    available: "Learning service online",
    unavailable: "Learning service unavailable",
    "invalid-response": "Learning service contract mismatch"
  }[apiAvailability];

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/" aria-label="Career Atlas home">
          <span className={styles.mark} aria-hidden="true">CA</span>
          <span className={styles.brandText}>
            <strong>Career Atlas</strong>
            <span>AI career learning system</span>
          </span>
        </Link>
        <div className={styles.headerActions}>
          <span
            className={`${styles.status} service-state-${apiAvailability} ${apiAvailability === "available" ? styles.statusOnline : ""}`}
            role="status"
          >
            {availabilityLabel}
          </span>
          <Link className="button button-quiet" href="/app">Resume</Link>
        </div>
      </header>

      <section className={styles.hero} aria-labelledby="learning-product-heading">
        <div>
          <p className="eyebrow">Career preparation that separates planning signals from proof</p>
          <h1 id="learning-product-heading">Learn the role. Prove you can do the work.</h1>
          <p className={styles.heroLead}>
            Resolve the exact career Target, use self-report to prioritize diagnosis, and let Career
            Atlas rebuild the path as stronger evidence, assessments, reviews, constraints, and
            available time change. Readiness stays locked until the required proof exists.
          </p>
          <div className={styles.actions}>
            <Link className="button button-primary" href="/onboarding">Build your personal path</Link>
            <Link className="button button-quiet" href="/app/roadmap">See the learning workspace</Link>
          </div>
        </div>

        <aside className={styles.heroPanel} aria-label="Available career tracks">
          <p className={styles.panelLabel}>Provisional engineering catalog</p>
          <div className={styles.trackList}>
            {tracks.map(([title, description]) => (
              <div className={styles.track} key={title}>
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section className={styles.workflow} aria-labelledby="workflow-title">
        <div className={styles.workflowHeader}>
          <h2 id="workflow-title">One control loop toward credible role evidence.</h2>
          <p>
            Curriculum is a projection of the resolved Target and current evidence state. Learner
            attestation can change what comes next, but only independent validated evidence may
            eventually support mastery and readiness.
          </p>
        </div>
        <div className={styles.steps}>
          {steps.map(([number, title, description]) => (
            <article className={styles.step} key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <span>Career Atlas is validation-locked; it does not certify employment or current role readiness.</span>
        <nav aria-label="Publication information">
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/status">Status</Link>
        </nav>
      </footer>
    </main>
  );
}
