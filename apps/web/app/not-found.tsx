import Link from "next/link";

import styles from "./disclosure.module.css";

export default function NotFound() {
  return (
    <main className={styles.shell}>
      <header className={styles.hero}>
        <p className="eyebrow">404 · Route not found</p>
        <h1>This path is outside the current learning map.</h1>
        <p>
          The public beta exposes only the learning workspace, disclosures, and live service status.
        </p>
      </header>
      <div className={styles.links}>
        <Link href="/">Return to Career Atlas</Link>
        <Link href="/status">Check service status</Link>
      </div>
    </main>
  );
}
