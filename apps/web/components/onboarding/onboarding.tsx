"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { LEARNING_SESSION_STORAGE_KEY } from "../../lib/learning-session";
import { publishPlanSaved } from "../../lib/learning-events";
import { createPlan, loadRoles } from "../../lib/platform-client";
import type { RoleView } from "../../lib/learning-contract";
import styles from "./onboarding.module.css";

export function Onboarding() {
  const router = useRouter();
  const [roles, setRoles] = useState<readonly RoleView[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [learnerName, setLearnerName] = useState("");
  const [experienceSummary, setExperienceSummary] = useState("");
  const [weeklyHours, setWeeklyHours] = useState(8);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadRoles()
        .then((catalog) => {
          setRoles(catalog);
          setSelectedRoleId((current) => current || catalog[0]?.id || "");
        })
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "The career catalog could not load.");
        })
        .finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(handle);
  }, []);

  const selectedRole = useMemo(
    () => roles.find((role) => role.id === selectedRoleId),
    [roles, selectedRoleId]
  );

  useEffect(() => {
    if (selectedRole === undefined) {
      return;
    }
    setRatings(Object.fromEntries(selectedRole.competencies.map((item) => [item.id, 0])));
  }, [selectedRole]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedRole === undefined) {
      setError("Choose an available career track first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const plan = await createPlan({
        learner_name: learnerName,
        target_role: selectedRole.id,
        weekly_hours: weeklyHours,
        experience_summary: experienceSummary,
        ratings: selectedRole.competencies.map((competency) => ({
          competency_id: competency.id,
          score: ratings[competency.id] ?? 0
        }))
      });
      window.localStorage.setItem(LEARNING_SESSION_STORAGE_KEY, plan.state_token);
      publishPlanSaved();
      router.push("/app");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The learning plan could not be created.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/">Career Atlas</Link>
        <Link className={styles.back} href="/app">Resume existing workspace →</Link>
      </header>

      <section className={styles.intro}>
        <p className="eyebrow">Onboarding · career target first</p>
        <h1>Choose the role. Then we build the path around you.</h1>
        <p>
          Your target role defines the competency graph. Your current evidence, assessment results,
          learning capacity, and completed work determine the sequence inside that graph.
        </p>
      </section>

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <form className={styles.form} onSubmit={submit}>
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">01 · Target</p>
              <h2>Which job do you want to become ready for?</h2>
              <p>The API catalog is the source of truth; this is not a decorative selector.</p>
            </div>
          </div>
          <div className={styles.tracks}>
            {loading ? <p>Loading career tracks…</p> : null}
            {roles.map((role) => (
              <label
                className={`${styles.track} ${selectedRoleId === role.id ? styles.trackSelected : ""}`}
                key={role.id}
              >
                <input
                  type="radio"
                  name="target-role"
                  value={role.id}
                  checked={selectedRoleId === role.id}
                  onChange={() => setSelectedRoleId(role.id)}
                />
                <span>{role.competencies.length} competencies</span>
                <strong>{role.title}</strong>
                <p>{role.summary}</p>
              </label>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">02 · Context</p>
              <h2>Tell the engine what you are starting with.</h2>
              <p>Enough context to individualize the work without turning onboarding into a résumé form.</p>
            </div>
          </div>
          <div className={styles.profileGrid}>
            <div className={styles.field}>
              <label htmlFor="learner-name">Name</label>
              <input
                id="learner-name"
                minLength={2}
                maxLength={80}
                required
                value={learnerName}
                onChange={(event) => setLearnerName(event.target.value)}
                placeholder="Your name"
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="weekly-hours">Weekly learning capacity · {weeklyHours} hours</label>
              <input
                id="weekly-hours"
                type="range"
                min={2}
                max={40}
                step={1}
                value={weeklyHours}
                onChange={(event) => setWeeklyHours(Number(event.target.value))}
              />
            </div>
            <div className={`${styles.field} ${styles.fieldWide}`}>
              <label htmlFor="experience-summary">Current experience, constraints, and transition goal</label>
              <textarea
                id="experience-summary"
                rows={4}
                maxLength={600}
                value={experienceSummary}
                onChange={(event) => setExperienceSummary(event.target.value)}
                placeholder="Example: embedded engineer with strong C/C++ and CI experience, moving toward AI application engineering; limited production Python experience."
              />
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">03 · Evidence baseline</p>
              <h2>Rate only what you can currently defend.</h2>
              <p>Self-rating is provisional. Assessments and completed work can recalibrate the plan later.</p>
            </div>
          </div>
          <div className={styles.competencies}>
            {selectedRole?.competencies.map((competency) => (
              <label className={styles.competency} key={competency.id}>
                <span>
                  <strong>{competency.name}</strong>
                  <small>{competency.description}</small>
                </span>
                <select
                  aria-label={`${competency.name} self-rating`}
                  value={ratings[competency.id] ?? 0}
                  onChange={(event) =>
                    setRatings((current) => ({ ...current, [competency.id]: Number(event.target.value) }))
                  }
                >
                  <option value={0}>0 · No evidence</option>
                  <option value={1}>1 · Aware</option>
                  <option value={2}>2 · Guided</option>
                  <option value={3}>3 · Independent</option>
                  <option value={4}>4 · Defensible</option>
                </select>
              </label>
            ))}
          </div>
        </section>

        <footer className={styles.footer}>
          <p>
            The first plan is a starting hypothesis. It should change as you complete projects,
            submit evidence, take calibrations, or change your available time and focus.
          </p>
          <button className="button button-primary" type="submit" disabled={loading || submitting || selectedRole === undefined}>
            {submitting ? "Building your workspace…" : "Build my learning workspace"}
          </button>
        </footer>
      </form>
    </main>
  );
}
