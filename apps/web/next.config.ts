import type { NextConfig } from "next";

import { BROWSER_SECURITY_HEADERS } from "./server/security/headers";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [...BROWSER_SECURITY_HEADERS]
      }
    ];
  }
};

export default nextConfig;
