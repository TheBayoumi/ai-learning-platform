import type { Metadata } from "next";
import type { ReactNode } from "react";

import { readSiteUrl } from "../server/config/site-url";
import "./globals.css";

const siteUrl = readSiteUrl();

export const metadata: Metadata = {
  metadataBase: siteUrl,
  applicationName: "Career Atlas",
  title: {
    default: "Career Atlas · AI Career Learning",
    template: "%s · Career Atlas"
  },
  description:
    "Choose a career track, diagnose your current evidence, follow a learner-specific roadmap, build projects, calibrate mastery, and prepare for the role with bounded AI coaching.",
  alternates: { canonical: "/" },
  category: "education",
  keywords: [
    "career learning",
    "adaptive learning",
    "AI tutor",
    "career roadmap",
    "competency mastery"
  ],
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Career Atlas",
    title: "Career Atlas · AI Career Learning",
    description:
      "A role-driven learning system that adapts curriculum, projects, assessment, and evidence to the learner."
  },
  twitter: {
    card: "summary",
    title: "Career Atlas · AI Career Learning",
    description:
      "Choose a role, close competency gaps, build proof, and become ready to do the work."
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
