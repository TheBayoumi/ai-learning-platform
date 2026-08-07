import type { Metadata } from "next";
import Link from "next/link";

import styles from "../disclosure.module.css";

export const metadata: Metadata = {
  title: "Privacy",
  description: "How the Career Atlas public beta handles learner state, cookies, and AI tutor data.",
  alternates: { canonical: "/privacy" }
};

export default function PrivacyPage() {
  return (
    <main className={styles.shell}>
      <nav className={styles.navigation} aria-label="Privacy navigation">
        <Link href="/">← Career Atlas</Link>
        <span>Last updated: August 7, 2026</span>
      </nav>

      <header className={styles.hero}>
        <p className="eyebrow">Public beta disclosure</p>
        <h1>Privacy without hidden claims.</h1>
        <p>
          Career Atlas currently provides an anonymous career-learning beta. This notice explains
          the data paths implemented in the product today; it does not describe planned identity,
          billing, or analytics features that do not yet exist.
        </p>
      </header>

      <p className={styles.notice}>
        Use an alias and do not enter passwords, API keys, private source code, medical data,
        government identifiers, or confidential employer information.
      </p>

      <div className={styles.sections}>
        <section>
          <h2>Information you provide</h2>
          <ul>
            <li>A preferred name or alias, experience summary, competency ratings, and weekly availability.</li>
            <li>Mission reflections, criteria selections, confidence ratings, and evidence references.</li>
            <li>Tutor questions and short conversation history when you use bounded AI coaching.</li>
          </ul>
          <p>
            Evidence references should identify your own work without embedding secrets or private
            repository credentials. The beta does not request payment information or a government ID.
          </p>
        </section>

        <section>
          <h2>Browser storage and cookies</h2>
          <ul>
            <li>
              The browser stores the current signed learning-state token in local storage so the
              plan can be resumed after a refresh.
            </li>
            <li>
              The same-origin proxy creates a random anonymous account identifier in an HttpOnly,
              SameSite=Lax cookie. Browser JavaScript cannot read that cookie.
            </li>
            <li>
              Tutor conversation history is held in page memory for the current tab and is cleared
              when you clear the panel or close/reload the page.
            </li>
          </ul>
        </section>

        <section>
          <h2>Server storage modes</h2>
          <p>
            In signed-state mode, the browser token carries the resumable plan projection. In
            PostgreSQL mode, the server stores anonymous account records, versioned learner
            snapshots, append-only learning events, idempotency data, and transactional outbox
            records. The active deployment mode is controlled server-side.
          </p>
        </section>

        <section>
          <h2>AI tutor processing</h2>
          <p>
            When tutoring is enabled, your tutor message and up to six recent browser-held turns are
            sent through the Career Atlas API to the configured AI model provider. The server adds a
            minimized learning context containing the target role, current mission title and
            acceptance criteria, priority gaps, and recent evidence labels. It intentionally excludes
            the learner name, account identifier, state token, profile free text, mission objective,
            deliverable text, artifact location, and reflections.
          </p>
          <p>
            AI output is guidance only. It is not stored as accepted evidence and cannot change
            mastery, assessment, curriculum, or readiness state.
          </p>
        </section>

        <section>
          <h2>Analytics, advertising, and sharing</h2>
          <p>
            This release does not include advertising or third-party behavioral analytics code.
            Data is shared only with infrastructure and model providers required to operate the
            requested feature. Provider processing is subject to the configuration and terms of the
            connected deployment account.
          </p>
        </section>

        <section>
          <h2>Retention and deletion limits</h2>
          <p>
            You can remove local storage and the anonymous cookie through your browser&apos;s site-data
            controls. The current beta does not yet provide a self-service workflow that proves and
            deletes an anonymous durable PostgreSQL account across devices. Therefore, do not use the
            beta for sensitive personal or employer data. A private request channel and deletion
            workflow are required before production identity features are introduced.
          </p>
        </section>

        <section>
          <h2>Security and age boundary</h2>
          <p>
            The application uses same-origin server mediation, security headers, bounded request
            sizes, server-only provider credentials, and fail-closed validation. No internet service
            can guarantee absolute security. Career Atlas is designed for adult career learning and
            is not directed to children.
          </p>
        </section>

        <section>
          <h2>Questions and changes</h2>
          <p>
            Technical issues may be reported through the public project repository, but never post
            personal data or credentials there. Material changes to these data paths will update this
            notice and its date before the changed behavior is published.
          </p>
        </section>
      </div>

      <div className={styles.links}>
        <Link href="/terms">Terms</Link>
        <Link href="/status">Service status</Link>
        <Link href="/">Return to the platform</Link>
      </div>
    </main>
  );
}
