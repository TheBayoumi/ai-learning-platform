import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Career Atlas · AI Career Learning Platform",
  description:
    "Diagnose role gaps, generate learner-unique practical missions, and build evidence toward a career target."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
