import type { Metadata } from "next";
import type { ReactNode } from "react";

import { readSiteUrl } from "../server/config/site-url";
import "./globals.css";
import "./adaptive-curriculum.css";
import "./assessment-calibration.css";

const siteUrl = readSiteUrl();

export const metadata: Metadata = {
  metadataBase: siteUrl,
  applicationName: "Career Atlas",
  title: {
    default: "Career Atlas · Adaptive AI Career Learning",
    template: "%s · Career Atlas"
  },
  description:
    "Diagnose role gaps, follow learner-unique practical missions, collect evidence, calibrate knowledge, and use bounded AI coaching without employment-certification claims.",
  alternates: { canonical: "/" },
  category: "education",
  keywords: [
    "adaptive learning",
    "career development",
    "Python backend",
    "competency assessment",
    "AI tutor"
  ],
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Career Atlas",
    title: "Career Atlas · Adaptive AI Career Learning",
    description:
      "A persistent career-learning beta with adaptive missions, evidence tracking, assessment calibration, and bounded AI coaching."
  },
  twitter: {
    card: "summary",
    title: "Career Atlas · Adaptive AI Career Learning",
    description:
      "Adaptive missions, evidence tracking, calibration, and bounded AI coaching for a career target."
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1
    }
  }
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
