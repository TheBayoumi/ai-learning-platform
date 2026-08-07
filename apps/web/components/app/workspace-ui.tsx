"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useCareerApp } from "./app-provider";
import styles from "./workspace.module.css";

export function PageHeader({
  eyebrow,
  title,
  description,
  action
}: Readonly<{
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}>) {
  return (
    <header className={styles.header}>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}

export function NoPlan() {
  return (
    <section className={styles.empty}>
      <div className={styles.emptyInner}>
        <p className="eyebrow">No active career plan</p>
        <h2>Choose the role before opening the workspace.</h2>
        <p>
          Onboarding creates the learner-specific competency baseline and first dynamic mission.
        </p>
        <Link className="button button-primary" href="/onboarding">Choose a career track</Link>
      </div>
    </section>
  );
}

export function WithPlan({ children }: Readonly<{ children: ReactNode }>) {
  const { plan } = useCareerApp();
  return plan === null ? <NoPlan /> : children;
}

export function Metric({
  label,
  value,
  note
}: Readonly<{ label: string; value: string; note: string }>) {
  return (
    <article className={styles.metric}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
