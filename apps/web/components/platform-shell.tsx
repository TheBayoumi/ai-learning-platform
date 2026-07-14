import "server-only";

import type { ApiAvailability } from "../server/health/runtime-health";

interface StatusCopy {
  readonly label: string;
  readonly description: string;
}

const STATUS_COPY = {
  available: {
    label: "Local API available",
    description: "The local API returned the expected liveness response."
  },
  unavailable: {
    label: "Local API unavailable",
    description:
      "The local API could not be confirmed within the local check window. Check that it is running, then reload this page."
  },
  "invalid-response": {
    label: "Local API response invalid",
    description:
      "The local API response did not match the expected liveness contract. Check the API version, then reload this page."
  }
} satisfies Record<ApiAvailability, StatusCopy>;

interface PlatformShellProps {
  readonly apiAvailability: ApiAvailability;
}

export function PlatformShell({ apiAvailability }: PlatformShellProps) {
  const status = STATUS_COPY[apiAvailability];

  return (
    <main className="platform-shell">
      <header className="platform-header">
        <p className="eyebrow">Technical foundation</p>
        <h1>AI Career Learning Platform</h1>
        <p className="lede">
          Role-neutral local runtime status for the platform foundation.
        </p>
      </header>

      <section
        className="api-status"
        data-api-state={apiAvailability}
        aria-labelledby="api-integration-heading"
      >
        <div className="section-heading">
          <p className="section-index">01</p>
          <h2 id="api-integration-heading">API integration</h2>
        </div>

        <div
          className="status-detail"
          role="status"
          aria-atomic="true"
          aria-labelledby="api-status-label"
          aria-describedby="api-status-description"
        >
          <div className="status-line">
            <span className="status-marker" aria-hidden="true" />
            <p id="api-status-label" className="status-label">
              {status.label}
            </p>
          </div>
          <p id="api-status-description" className="status-description">
            {status.description}
          </p>
        </div>
      </section>

      <section
        className="foundation-boundary"
        aria-labelledby="foundation-boundary-heading"
      >
        <div className="section-heading">
          <p className="section-index">02</p>
          <h2 id="foundation-boundary-heading">Foundation boundary</h2>
        </div>
        <p>
          This status reports local process liveness only. No learner, role, or
          learning functionality is available in this foundation phase.
        </p>
      </section>
    </main>
  );
}
