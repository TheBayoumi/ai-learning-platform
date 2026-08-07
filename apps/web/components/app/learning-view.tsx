"use client";

import { type FormEvent, useState } from "react";

import { completeActivity } from "../../lib/platform-client";
import { TutorPanel } from "../tutor-panel";
import { useCareerApp } from "./app-provider";
import { NoPlan, PageHeader } from "./workspace-ui";
import styles from "./workspace.module.css";

export function LearningView() {
  const { plan, commitPlan } = useCareerApp();
  const [reflection, setReflection] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [criteriaMet, setCriteriaMet] = useState<readonly string[]>([]);
  const [confidence, setConfidence] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (plan === null) {
    return <NoPlan />;
  }

  const activity = plan.current_activity;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (activity === null) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await completeActivity({
        state_token: plan.state_token,
        activity_id: activity.id,
        reflection,
        evidence_reference: evidenceReference,
        criteria_met: criteriaMet,
        confidence
      });
      commitPlan(next);
      setReflection("");
      setEvidenceReference("");
      setCriteriaMet([]);
      setConfidence(0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evidence could not be recorded.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Learn"
        title={activity === null ? "Your active queue is clear." : activity.title}
        description={
          activity === null
            ? "Use the roadmap to replan focus or wait for the next scheduled review."
            : activity.rationale || "This mission is selected from your current role gaps and learning state."
        }
      />

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      {activity === null ? null : (
        <section className={styles.grid2}>
          <article className={styles.activity}>
            <div className={styles.activityMeta}>
              <span className={styles.pill}>{activity.kind}</span>
              <span className={styles.pill}>{activity.competency_name}</span>
              <span className={styles.pill}>{activity.estimated_minutes} min</span>
              <span className={styles.pill}>generation {activity.generation}</span>
            </div>
            <span className={styles.label}>Objective</span>
            <h2>{activity.objective}</h2>
            <span className={styles.label}>Deliverable</span>
            <p>{activity.deliverable}</p>
            <span className={styles.label}>Acceptance criteria</span>
            <ul className={styles.criteria}>
              {activity.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
            </ul>
          </article>

          <article className={styles.formCard}>
            <span className={styles.label}>Evidence submission</span>
            <h2>Record what you actually proved.</h2>
            <form className={styles.form} onSubmit={submit}>
              <div className={styles.checks}>
                {activity.acceptance_criteria.map((criterion) => (
                  <label className={styles.check} key={criterion}>
                    <input
                      type="checkbox"
                      checked={criteriaMet.includes(criterion)}
                      onChange={(event) =>
                        setCriteriaMet((current) =>
                          event.target.checked
                            ? [...current, criterion]
                            : current.filter((item) => item !== criterion)
                        )
                      }
                    />
                    <span>{criterion}</span>
                  </label>
                ))}
              </div>

              <div className={styles.field}>
                <label htmlFor="reflection">Reflection</label>
                <textarea
                  id="reflection"
                  rows={5}
                  maxLength={1000}
                  value={reflection}
                  onChange={(event) => setReflection(event.target.value)}
                  placeholder="What did you build, what failed, what changed, and what can you now defend?"
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="evidence-reference">Evidence reference</label>
                <input
                  id="evidence-reference"
                  maxLength={500}
                  value={evidenceReference}
                  onChange={(event) => setEvidenceReference(event.target.value)}
                  placeholder="Repository, document, demo, or other reference"
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="confidence">Confidence · {confidence}/4</label>
                <input
                  id="confidence"
                  type="range"
                  min={0}
                  max={4}
                  step={1}
                  value={confidence}
                  onChange={(event) => setConfidence(Number(event.target.value))}
                />
              </div>

              <button className="button button-primary" disabled={busy} type="submit">
                {busy ? "Recording evidence…" : "Complete mission with evidence"}
              </button>
            </form>
          </article>
        </section>
      )}

      <TutorPanel />
    </div>
  );
}
