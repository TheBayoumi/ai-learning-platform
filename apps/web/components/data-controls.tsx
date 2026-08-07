"use client";

import { type FormEvent, useState } from "react";

import {
  clearLocalLearningState,
  deleteCurrentAnonymousAccount
} from "../lib/account-deletion";
import styles from "./data-controls.module.css";

export function DataControls() {
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await deleteCurrentAnonymousAccount(confirmation);
      clearLocalLearningState(window.localStorage);
      setConfirmation("");
      setMessage(
        result.deleted
          ? "The current anonymous server account and local learning state were deleted."
          : "No durable server account was found. Local learning state was cleared."
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The current anonymous account could not be deleted."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.control} aria-labelledby="delete-account-heading">
      <div>
        <p className="eyebrow">Current anonymous session</p>
        <h2 id="delete-account-heading">Delete this account&apos;s learning data</h2>
        <p>
          This removes the anonymous account identified by this browser&apos;s HttpOnly cookie. In
          PostgreSQL mode, dependent learner snapshots, events, and outbox records are deleted by
          database cascade. It does not identify or delete another browser or a future signed-in
          account.
        </p>
      </div>

      <form onSubmit={submit}>
        <label htmlFor="account-delete-confirmation">
          Type <strong>DELETE</strong> to confirm
        </label>
        <input
          id="account-delete-confirmation"
          autoComplete="off"
          spellCheck={false}
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
        />
        <button
          className="button button-primary"
          type="submit"
          disabled={busy || confirmation !== "DELETE"}
        >
          {busy ? "Deleting…" : "Delete current anonymous account"}
        </button>
      </form>

      {message !== null ? (
        <p className={styles.success} role="status">
          {message}
        </p>
      ) : null}
      {error !== null ? (
        <div className="error-banner" role="alert">
          <p>{error}</p>
        </div>
      ) : null}
    </section>
  );
}
