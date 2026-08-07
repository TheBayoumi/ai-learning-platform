import type { Metadata } from "next";
import Link from "next/link";

import { resolveRuntimeApiAvailability } from "../../server/health/runtime-health";
import styles from "../disclosure.module.css";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export const metadata: Metadata = {
  title: "Service status",
  description: "Current Career Atlas API health and operational boundaries.",
  alternates: { canonical: "/status" },
  robots: { index: true, follow: true }
};

const STATUS_COPY = {
  available: {
    title: "Core learning API available",
    detail:
      "The live health contract passed. Individual model-provider requests can still be limited or temporarily unavailable."
  },
  unavailable: {
    title: "Core learning API unavailable",
    detail:
      "The application could not reach a healthy API response within the bounded check. Existing browser state remains local, but new server actions may fail."
  },
  "invalid-response": {
    title: "Core learning API degraded",
    detail:
      "The API responded, but the health response did not match the expected contract. Product actions are treated as unsafe until the contract is restored."
  }
} as const;

export default async function StatusPage() {
  const availability = await resolveRuntimeApiAvailability();
  const copy = STATUS_COPY[availability];
  const className =
    availability === "available"
      ? `${styles.statusCard} ${styles.available}`
      : availability === "invalid-response"
        ? `${styles.statusCard} ${styles.degraded}`
        : `${styles.statusCard} ${styles.unavailable}`;

  return (
    <main className={styles.shell}>
      <nav className={styles.navigation} aria-label="Status navigation">
        <Link href="/">← Career Atlas</Link>
        <span>Live bounded health check</span>
      </nav>

      <header className={styles.hero}>
        <p className="eyebrow">Operational status</p>
        <h1>Current service health.</h1>
        <p>
          This page performs one no-retry server-side health request. It is not an uptime SLA and
          does not trigger a paid tutor-model request.
        </p>
      </header>

      <section className={className} aria-live="polite">
        <span>Observed state</span>
        <strong>{copy.title}</strong>
        <p>{copy.detail}</p>
      </section>

      <div className={styles.links}>
        <Link href="/privacy">Privacy</Link>
        <Link href="/terms">Terms</Link>
        <Link href="/">Return to the platform</Link>
      </div>
    </main>
  );
}
