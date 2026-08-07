import type { Metadata } from "next";
import Link from "next/link";

import styles from "../disclosure.module.css";

export const metadata: Metadata = {
  title: "Terms",
  description: "Terms and claim boundaries for the Career Atlas public beta.",
  alternates: { canonical: "/terms" }
};

export default function TermsPage() {
  return (
    <main className={styles.shell}>
      <nav className={styles.navigation} aria-label="Terms navigation">
        <Link href="/">← Career Atlas</Link>
        <span>Last updated: August 7, 2026</span>
      </nav>

      <header className={styles.hero}>
        <p className="eyebrow">Public beta terms</p>
        <h1>Use the platform as a learning tool, not a credential.</h1>
        <p>
          These terms define the current bounded beta. By using Career Atlas, you agree to use it
          lawfully, protect confidential information, and treat its outputs as guidance that still
          requires your own verification.
        </p>
      </header>

      <div className={styles.sections}>
        <section>
          <h2>Beta scope</h2>
          <p>
            Career Atlas provides role-gap diagnosis, adaptive mission sequencing, learner-attested
            evidence capture, assessment calibration, and optional bounded AI coaching. Features may
            change as the product is tested. Availability is not guaranteed and the service may be
            paused to protect security, cost, or data integrity.
          </p>
        </section>

        <section>
          <h2>No employment or certification guarantee</h2>
          <p>
            A plan, score, completed mission, evidence entry, or tutor response does not certify
            mastery, guarantee employment, replace an accredited qualification, or represent an
            employer&apos;s hiring decision. Readiness claims require evidence and validation beyond the
            current beta.
          </p>
        </section>

        <section>
          <h2>AI limitations</h2>
          <p>
            AI responses can be incomplete, outdated, or wrong. Verify technical guidance against
            primary documentation, tests, and the actual runtime environment. The tutor cannot accept
            evidence, change mastery, or mark you job-ready. Do not rely on the platform for medical,
            legal, financial, safety-critical, or emergency decisions.
          </p>
        </section>

        <section>
          <h2>Your responsibilities</h2>
          <ul>
            <li>Submit only content you have the right to use and evaluate.</li>
            <li>Do not upload or paste credentials, personal identifiers, or confidential employer data.</li>
            <li>Do not attempt to bypass account boundaries, limits, security controls, or provider safeguards.</li>
            <li>Do not use the service to generate malware, abuse infrastructure, impersonate others, or violate law.</li>
            <li>Independently verify work before using it in production or presenting it to an employer.</li>
          </ul>
        </section>

        <section>
          <h2>Your work and platform output</h2>
          <p>
            You retain responsibility for the work and references you submit. The beta uses that
            information only to provide the requested learning flow. Generated plans and tutor output
            may resemble output provided to other users and are supplied without exclusivity.
          </p>
        </section>

        <section>
          <h2>Abuse, limits, and suspension</h2>
          <p>
            Requests may be rate-limited or rejected when the service reaches capacity. Access may be
            restricted when activity threatens security, provider spend, data integrity, or other
            users. Attempts to evade limits may result in the anonymous session being blocked or reset.
          </p>
        </section>

        <section>
          <h2>Warranty and liability boundary</h2>
          <p>
            The beta is provided on an as-available basis. To the extent permitted by applicable law,
            no warranty is made that outputs are accurate, complete, uninterrupted, or suitable for a
            specific job or production system. You are responsible for backups, review, testing, and
            decisions made from platform output.
          </p>
        </section>

        <section>
          <h2>Changes</h2>
          <p>
            Material changes to these terms will be reflected on this page before the changed behavior
            is presented as generally available. Continuing to use the beta after an update means you
            accept the updated terms.
          </p>
        </section>
      </div>

      <div className={styles.links}>
        <Link href="/privacy">Privacy</Link>
        <Link href="/status">Service status</Link>
        <Link href="/">Return to the platform</Link>
      </div>
    </main>
  );
}
