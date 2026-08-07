import type { MetadataRoute } from "next";

import { readSiteUrl } from "../server/config/site-url";

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = readSiteUrl();
  return [
    { url: new URL("/", siteUrl).toString(), changeFrequency: "weekly", priority: 1 },
    { url: new URL("/privacy", siteUrl).toString(), changeFrequency: "monthly", priority: 0.4 },
    { url: new URL("/terms", siteUrl).toString(), changeFrequency: "monthly", priority: 0.4 },
    { url: new URL("/status", siteUrl).toString(), changeFrequency: "daily", priority: 0.5 }
  ];
}
