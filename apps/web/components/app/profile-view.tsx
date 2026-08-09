"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteAccount, exportAccount } from "../../lib/platform-client";
import { useCareerApp } from "./app-provider";
import { NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

export function ProfileView() {
  const router = useRouter();
  const { plan, clearPlan } = useCareerApp();
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (plan === null) {
    return <NoPlan />;
  }

  const downloadExport = async () => {
    setExportBusy(true);
    setError(null);
    try {
      const data = await exportAccount();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "career-atlas-account-export.json";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The learner data export failed.");
    } finally {
      setExportBusy(false);
    }
  };

  const removeAccount = async () => {
    if (confirmation !== "DELETE") {
      setError("Type DELETE exactly before removing the anonymous learner account.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteAccount();
      clearPlan();
      router.push("/onboarding");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The learner account could not be deleted.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Profile"
        title={plan.learner_name}
        description="Your current target, learning capacity, and data controls live here. Changing career track starts a new role graph rather than mutating evidence into a different job."
        action={<Link className="button button-primary" href="/onboarding">Choose a different track</Link>}
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <section className={styles.grid2}>
        <article className={styles.card}>
          <span className={styles.label}>Active learner profile</span>
          <h2>{plan.role.title}</h2>
          <ul className={styles.list}>
            <li>
              <span className={styles.itemTitle}><strong>Career track</strong><small>{plan.role.id}</small></span>
              <span className={styles.score}>{plan.role.competencies.length} skills</span>
            </li>
            <li>
              <span className={styles.itemTitle}><strong>Weekly capacity</strong><small>Used to bound active curriculum volume</small></span>
              <span className={styles.score}>{plan.weekly_hours}h</span>
            </li>
            <li>
              <span className={styles.itemTitle}><strong>Plan revision</strong><small>Roadmap rebuild generation</small></span>
              <span className={styles.score}>{plan.plan_revision}</span>
            </li>
            <li>
              <span className={styles.itemTitle}><strong>Evidence records</strong><small>Learner-attested work retained in current state</small></span>
              <span className={styles.score}>{plan.evidence_history.length}</span>
            </li>
          </ul>
          <div className={styles.actions}>
            <Link className="button button-quiet" href="/app/roadmap">Adjust capacity & focus</Link>
          </div>
        </article>

        <article className={`${styles.formCard} ${styles.danger}`}>
          <span className={styles.label}>Data controls</span>
          <h2>Export or delete this learner account</h2>
          <p>
            Export verifies the current PostgreSQL snapshot against append-only replay before the
            browser receives a redacted JSON copy. Export does not include account cookies, provider
            credentials, or server secrets.
          </p>
          <div className={styles.actions}>
            <button
              className="button button-quiet"
              type="button"
              disabled={exportBusy || busy}
              onClick={() => void downloadExport()}
            >
              {exportBusy ? "Preparing export…" : "Download my data"}
            </button>
          </div>
          <h2>Delete this anonymous learner account</h2>
          <p>
            This removes the server-side account and its durable learner state, events, and outbox records.
            The browser session is cleared only after the server confirms deletion.
          </p>
          <div className={styles.form}>
            <div className={styles.field}>
              <label htmlFor="delete-confirmation">Type DELETE to confirm</label>
              <input
                id="delete-confirmation"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                autoComplete="off"
              />
            </div>
            <button
              className="button button-quiet"
              type="button"
              disabled={busy || confirmation !== "DELETE"}
              onClick={() => void removeAccount()}
            >
              {busy ? "Deleting…" : "Delete learner data"}
            </button>
          </div>
        </article>
      </section>
    </div>
  );
}
