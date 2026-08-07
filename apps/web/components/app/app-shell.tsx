"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useCareerApp } from "./app-provider";
import styles from "./app-shell.module.css";

const navigation = [
  ["/app", "Dashboard"],
  ["/app/learn", "Learn"],
  ["/app/roadmap", "Roadmap"],
  ["/app/projects", "Projects"],
  ["/app/assessments", "Assessments"],
  ["/app/readiness", "Readiness"],
  ["/app/profile", "Profile"]
] as const;

function isActive(pathname: string, href: string): boolean {
  return href === "/app" ? pathname === href : pathname.startsWith(href);
}

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const { plan, loading, error } = useCareerApp();

  return (
    <div className={styles.frame}>
      <aside className={styles.sidebar}>
        <Link className={styles.brand} href="/">
          <span className={styles.mark} aria-hidden="true">CA</span>
          <span className={styles.brandText}>
            <strong>Career Atlas</strong>
            <span>Learning workspace</span>
          </span>
        </Link>

        <nav className={styles.nav} aria-label="Learning workspace">
          {navigation.map(([href, label]) => (
            <Link className={isActive(pathname, href) ? styles.active : undefined} href={href} key={href}>
              <span>{label}</span>
              <span className={styles.dot} aria-hidden="true" />
            </Link>
          ))}
        </nav>

        <div className={styles.identity}>
          <strong>{plan?.learner_name ?? "No active learner plan"}</strong>
          <span>{plan?.role.title ?? "Choose a career track to start the workspace."}</span>
        </div>
      </aside>

      <main className={styles.content}>
        <header className={styles.topbar}>
          <span className={styles.breadcrumb}>
            {plan === null ? "Career workspace" : `${plan.role.title} · revision ${plan.plan_revision}`}
          </span>
          <div className={styles.topActions}>
            {plan !== null ? (
              <span className={styles.readiness}>
                readiness <strong>{plan.readiness_percent}%</strong>
              </span>
            ) : null}
            <Link className="button button-quiet" href="/onboarding">
              {plan === null ? "Start a plan" : "Change track"}
            </Link>
          </div>
        </header>

        <div className={styles.workspace}>
          {loading ? <div className={styles.loading}>Loading your learning state…</div> : null}
          {!loading && error !== null ? (
            <div className="error-banner" role="alert"><p>{error}</p></div>
          ) : null}
          {!loading && error === null ? children : null}
        </div>
      </main>
    </div>
  );
}
