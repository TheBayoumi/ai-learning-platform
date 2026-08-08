"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { publishPlanSaved } from "../../lib/learning-events";
import { LEARNING_SESSION_STORAGE_KEY } from "../../lib/learning-session";
import type { RoleView } from "../../lib/learning-contract";
import { createPlan, loadRoles } from "../../lib/platform-client";
import styles from "./onboarding.module.css";

interface TargetDraft {
  readonly seniority: string;
  readonly laborMarket: string;
  readonly timelineWeeks: number;
  readonly geography: string;
  readonly stackOverlays: string;
  readonly industryOverlay: string;
  readonly companyOverlay: string;
}

const EMPTY_TARGET: TargetDraft = {
  seniority: "",
  laborMarket: "",
  timelineWeeks: 20,
  geography: "",
  stackOverlays: "",
  industryOverlay: "",
  companyOverlay: ""
};

function initialRatings(role: RoleView | undefined): Record<string, number> {
  if (role === undefined) {
    return {};
  }
  return Object.fromEntries(role.competencies.map((item) => [item.id, 0]));
}

function targetDraft(role: RoleView | undefined): TargetDraft {
  if (role === undefined) {
    return EMPTY_TARGET;
  }
  return {
    seniority: role.default_target.seniority,
    laborMarket: role.default_target.labor_market,
    timelineWeeks: role.default_target.timeline_weeks,
    geography: role.default_target.geography,
    stackOverlays: role.default_target.stack_overlays.join(", "),
    industryOverlay: role.default_target.industry_overlay ?? "",
    companyOverlay: role.default_target.company_overlay ?? ""
  };
}

function overlays(value: string): readonly string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function Onboarding() {
  const router = useRouter();
  const [roles, setRoles] = useState<readonly RoleView[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [target, setTarget] = useState<TargetDraft>(EMPTY_TARGET);
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
          const firstRole = catalog[0];
          setRoles(catalog);
          setSelectedRoleId(firstRole?.id ?? "");
          setTarget(targetDraft(firstRole));
          setRatings(initialRatings(firstRole));
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

  const selectRole = (role: RoleView) => {
    setSelectedRoleId(role.id);
    setTarget(targetDraft(role));
    setRatings(initialRatings(role));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedRole === undefined) {
      setError("Choose an available career track first.");
      return;
    }
    const stackOverlays = overlays(target.stackOverlays);
    if (stackOverlays.length === 0) {
      setError("Resolve at least one stack overlay before the platform can build a plan.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const plan = await createPlan({
        learner_name: learnerName,
        target_role: selectedRole.id,
        target: {
          seniority: target.seniority,
          labor_market: target.laborMarket,
          timeline_weeks: target.timelineWeeks,
          geography: target.geography,
          stack_overlays: stackOverlays,
          industry_overlay: target.industryOverlay.trim() || null,
          company_overlay: target.companyOverlay.trim() || null
        },
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
        <p className="eyebrow">Onboarding · resolve before planning</p>
        <h1>Define the exact job target before the engine builds anything.</h1>
        <p>
          A role title alone is underspecified. Career Atlas binds every plan to a role version,
          seniority, labor market, timeline, geography, and explicit stack or domain overlays.
        </p>
      </section>

      {error !== null ? <div className="error-banner" role="alert"><p>{error}</p></div> : null}

      <form className={styles.form} onSubmit={submit}>
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">01 · Role profile candidate</p>
              <h2>Which work outcome are you targeting?</h2>
              <p>
                These profiles are engineering-available but provisional until the external role
                validation gates pass. Selecting one does not create a readiness claim.
              </p>
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
                  onChange={() => selectRole(role)}
                />
                <span>{role.competencies.length} competencies · {role.validation_state}</span>
                <strong>{role.title}</strong>
                <p>{role.summary}</p>
              </label>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">02 · Resolved Target</p>
              <h2>Make the target specific enough to plan against.</h2>
              <p>
                Defaults come from the selected provisional role profile. Change them to match the
                actual market and constraints you intend to prepare for.
              </p>
            </div>
          </div>
          <div className={styles.profileGrid}>
            <div className={styles.field}>
              <label htmlFor="target-seniority">Seniority</label>
              <input
                id="target-seniority"
                required
                minLength={2}
                maxLength={160}
                value={target.seniority}
                onChange={(event) => setTarget((current) => ({ ...current, seniority: event.target.value }))}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="target-geography">Geography</label>
              <input
                id="target-geography"
                required
                minLength={2}
                maxLength={160}
                value={target.geography}
                onChange={(event) => setTarget((current) => ({ ...current, geography: event.target.value }))}
              />
            </div>
            <div className={`${styles.field} ${styles.fieldWide}`}>
              <label htmlFor="target-market">Labor market</label>
              <input
                id="target-market"
                required
                minLength={2}
                maxLength={160}
                value={target.laborMarket}
                onChange={(event) => setTarget((current) => ({ ...current, laborMarket: event.target.value }))}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="target-timeline">Preparation timeline · {target.timelineWeeks} weeks</label>
              <input
                id="target-timeline"
                type="range"
                min={1}
                max={104}
                step={1}
                value={target.timelineWeeks}
                onChange={(event) => setTarget((current) => ({ ...current, timelineWeeks: Number(event.target.value) }))}
              />
            </div>
            <div className={`${styles.field} ${styles.fieldWide}`}>
              <label htmlFor="target-stack">Stack overlays · comma separated</label>
              <textarea
                id="target-stack"
                required
                rows={3}
                value={target.stackOverlays}
                onChange={(event) => setTarget((current) => ({ ...current, stackOverlays: event.target.value }))}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="industry-overlay">Industry overlay · optional</label>
              <input
                id="industry-overlay"
                maxLength={160}
                value={target.industryOverlay}
                onChange={(event) => setTarget((current) => ({ ...current, industryOverlay: event.target.value }))}
                placeholder="Fintech, automotive, health…"
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="company-overlay">Company overlay · optional</label>
              <input
                id="company-overlay"
                maxLength={160}
                value={target.companyOverlay}
                onChange={(event) => setTarget((current) => ({ ...current, companyOverlay: event.target.value }))}
                placeholder="Only when preparing for a named employer"
              />
            </div>
          </div>
          {selectedRole === undefined ? null : (
            <p>
              <strong>Claim boundary:</strong> {selectedRole.default_target.scope} {" "}
              {selectedRole.default_target.exclusions.join(" ")}
            </p>
          )}
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className="eyebrow">03 · Learner context</p>
              <h2>Tell the engine what constraints it must plan around.</h2>
              <p>Context personalizes work selection; it cannot grant competency evidence.</p>
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
              <p className="eyebrow">04 · Self-report for diagnostic prioritization</p>
              <h2>Tell us where to investigate first—not what you have mastered.</h2>
              <p>
                Self-rating only changes planning priority. It never grants mastery, evidence,
                readiness, or completion credit.
              </p>
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
                  <option value={0}>0 · Start diagnosis here</option>
                  <option value={1}>1 · Familiar</option>
                  <option value={2}>2 · Some guided experience</option>
                  <option value={3}>3 · Usually independent</option>
                  <option value={4}>4 · I can defend prior work</option>
                </select>
              </label>
            ))}
          </div>
        </section>

        <footer className={styles.footer}>
          <p>
            The first curriculum is a planning hypothesis. Verified mastery and role readiness stay
            locked until independent, retention, transfer, provenance, and realistic-work evidence
            gates are implemented and passed.
          </p>
          <button className="button button-primary" type="submit" disabled={loading || submitting || selectedRole === undefined}>
            {submitting ? "Building your workspace…" : "Resolve target and build my workspace"}
          </button>
        </footer>
      </form>
    </main>
  );
}
