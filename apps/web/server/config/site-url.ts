import "server-only";

const DEFAULT_SITE_URL = "https://web-three-henna-34.vercel.app";

export function readSiteUrl(): URL {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim() || DEFAULT_SITE_URL;
  let url: URL;
  try {
    url = new URL(configured);
  } catch {
    throw new Error("NEXT_PUBLIC_SITE_URL must be an absolute URL.");
  }
  if (url.username !== "" || url.password !== "") {
    throw new Error("NEXT_PUBLIC_SITE_URL must not contain credentials.");
  }
  if (url.search !== "" || url.hash !== "") {
    throw new Error("NEXT_PUBLIC_SITE_URL must not contain a query or fragment.");
  }
  if (process.env.NODE_ENV === "production" && url.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_SITE_URL must use HTTPS in production.");
  }
  url.pathname = "/";
  return url;
}
