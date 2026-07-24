import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./adaptive-curriculum.css";

export const metadata: Metadata = {
  title: "Career Atlas · AI Career Learning Platform",
  description:
    "Diagnose role gaps, generate learner-unique practical missions, capture evidence, and adapt the curriculum toward a career target."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
