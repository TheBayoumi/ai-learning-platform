import "server-only";

import type { ApiAvailability } from "../server/health/runtime-health";
import { AssessmentCalibration } from "./assessment-calibration";
import { LearningPlatform } from "./learning-platform";
import { TutorPanel } from "./tutor-panel";

interface PlatformShellProps {
  readonly apiAvailability: ApiAvailability;
}

export function PlatformShell({ apiAvailability }: PlatformShellProps) {
  return (
    <main className="career-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Career Atlas home">
          <span className="brand-mark" aria-hidden="true">CA</span>
          <span>
            <strong>Career Atlas</strong>
            <small>AI learning platform</small>
          </span>
        </a>
        <p className="header-note">Learn the role. Prove the work. Close the gap.</p>
      </header>

      <section className="hero" id="top" aria-labelledby="hero-heading">
        <div className="hero-copy">
          <p className="eyebrow">Persistent career preparation</p>
          <h1 id="hero-heading">Your target role becomes a living training system.</h1>
          <p className="hero-lede">
            Diagnose your current evidence, receive a learner-unique sequence of practical
            missions, and calibrate planning signals without confusing a short assessment with
            employment certification.
          </p>
          <div className="hero-signals" aria-label="Platform capabilities">
            <span>Dynamic competency priorities</span>
            <span>Unique practical missions</span>
            <span>Evidence plus calibration</span>
          </div>
        </div>
        <aside className="hero-card" aria-label="Current launch track">
          <p>Launch track</p>
          <strong>Junior Python Backend Engineer</strong>
          <dl>
            <div>
              <dt>Competencies</dt>
              <dd>10</dd>
            </div>
            <div>
              <dt>Plan type</dt>
              <dd>Adaptive</dd>
            </div>
            <div>
              <dt>Signals</dt>
              <dd>Evidence + calibration</dd>
            </div>
          </dl>
        </aside>
      </section>

      <LearningPlatform apiAvailability={apiAvailability} />
      <TutorPanel />
      <AssessmentCalibration />

      <footer className="site-footer">
        <p>
          Career Atlas provides diagnosis, adaptive planning, bounded AI coaching,
          learner-attested evidence, and objective planning calibration. Tutor output is guidance,
          not accepted evidence or employment certification.
        </p>
      </footer>
    </main>
  );
}
