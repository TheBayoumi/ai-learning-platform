import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { auth0Client, oidcEnabled } from "./lib/auth0";

export async function proxy(request: NextRequest): Promise<Response> {
  if (!oidcEnabled()) {
    return NextResponse.next();
  }
  return auth0Client().middleware(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"]
};
