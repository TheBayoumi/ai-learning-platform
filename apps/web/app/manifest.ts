import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Career Atlas",
    short_name: "Career Atlas",
    description:
      "Adaptive career learning with practical missions, evidence tracking, calibration, and bounded AI coaching.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f1e8",
    theme_color: "#16231f",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml"
      }
    ]
  };
}
