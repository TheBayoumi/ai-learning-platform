import "server-only";

import { LearningPlatform } from "./learning-platform";
import type { ApiAvailability } from "../server/health/runtime-health";

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
            missions, and update your readiness as you complete defensible work.
          </p>
          <div className="hero-signals" aria-label="Platform capabilities">
            <span>Dynamic competency priorities</span>
            <span>Unique practical missions</span>
            <span>Evidence-based progress</span>
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
              <dt>Region</dt>
              <dd>Egypt / MENA + remote</dd>
            </div>
          </dl>
        </aside>
      </section>

      <LearningPlatform apiAvailability={apiAvailability} />

      <footer className="site-footer">
        <p>
          This first deployed slice provides diagnosis, personalized planning, and signed
          browser-resumable progress. Account persistence and AI tutoring are not represented
          as complete yet.
        </p>
      </footer>
    </main>
  );
}
