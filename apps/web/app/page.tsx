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
  ["01", "Choose the work", "Select the career role you actually want to perform, not a generic course category."],
  ["02", "Diagnose the gap", "Map current evidence and calibration signals against the role competency graph."],
  ["03", "Build proof", "Work through learner-specific missions, projects, reviews, and spaced evidence cycles."],
  ["04", "Earn readiness", "Track what is proven, what is weak, and what still blocks credible role readiness."]
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
            className={`${styles.status} ${apiAvailability === "available" ? styles.statusOnline : ""}`}
            role="status"
          >
            {availabilityLabel}
          </span>
          <Link className="button button-quiet" href="/app">Resume</Link>
        </div>
      </header>

      <section className={styles.hero}>
        <div>
          <p className="eyebrow">Career preparation that adapts to evidence</p>
          <h1>Learn the role. Prove you can do the work.</h1>
          <p className={styles.heroLead}>
            Choose a target career, show what you already know, and let Career Atlas continuously
            rebuild the path around your gaps, projects, assessments, evidence, and available time.
          </p>
          <div className={styles.actions}>
            <Link className="button button-primary" href="/onboarding">Choose your career track</Link>
            <Link className="button button-quiet" href="/app/roadmap">See the learning workspace</Link>
          </div>
        </div>

        <aside className={styles.heroPanel} aria-label="Available career tracks">
          <p className={styles.panelLabel}>Starter career catalog</p>
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
          <h2 id="workflow-title">One system from target role to credible readiness.</h2>
          <p>
            Curriculum is a projection of your current evidence state. Completing work, failing a
            calibration, changing capacity, or choosing a focus can change what comes next.
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
        <span>Career Atlas uses evidence and calibration signals; it does not certify employment.</span>
        <nav aria-label="Publication information">
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/status">Status</Link>
        </nav>
      </footer>
    </main>
  );
}
