import { randomUUID } from "node:crypto";

import { readApiBaseUrl } from "../../../../server/config/api-base";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const UPSTREAM_TIMEOUT_MS = 8_000;
const MAX_REQUEST_BYTES = 96 * 1024;
const MAX_RESPONSE_BYTES = 768 * 1024;
const ACCOUNT_COOKIE = "ai_platform_account";
const ACCOUNT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ALLOWED_PATHS = new Set([
  "roles",
  "plans",
  "plans/resume",
  "plans/replan",
  "progress",
  "assessments/start",
  "assessments/submit"
]);

const GET_PATHS = new Set(["roles"]);

type RouteContext = Readonly<{
  params: Promise<Readonly<{ path: string[] }>>;
}>;

type ProxyMethod = "GET" | "POST";

export async function GET(
  request: Request,
  context: RouteContext
): Promise<Response> {
  return proxyRequest(request, context, "GET");
}

export async function POST(
  request: Request,
  context: RouteContext
): Promise<Response> {
  return proxyRequest(request, context, "POST");
}

async function proxyRequest(
  request: Request,
  context: RouteContext,
  method: ProxyMethod
): Promise<Response> {
  const { path } = await context.params;
  const relativePath = path.join("/");
  if (!ALLOWED_PATHS.has(relativePath)) {
    return errorResponse(404, "PLATFORM_ROUTE_NOT_FOUND", "The platform route is not available.");
  }
  if (GET_PATHS.has(relativePath) !== (method === "GET")) {
    return errorResponse(405, "PLATFORM_METHOD_NOT_ALLOWED", "The request method is not allowed.");
  }

  const accountContext = method === "POST" ? resolveAccountContext(request) : null;
  let body: string | undefined;
  if (method === "POST") {
    body = await request.text();
    if (Buffer.byteLength(body, "utf8") > MAX_REQUEST_BYTES) {
      return errorResponse(413, "PLATFORM_REQUEST_TOO_LARGE", "The request is too large.");
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const upstreamUrl = new URL(`/api/v1/${relativePath}`, readApiBaseUrl());
    const upstream = await fetch(upstreamUrl, {
      method,
      headers: {
        accept: "application/json",
        ...(body === undefined ? {} : { "content-type": "application/json" }),
        ...(accountContext === null
          ? {}
          : {
              "x-platform-account-id": accountContext.accountId,
              "x-platform-command-id": randomUUID()
            })
      },
      body,
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
      signal: controller.signal
    });
    const contentType = upstream.headers.get("content-type")?.toLowerCase() ?? "";
    if (!contentType.startsWith("application/json")) {
      return errorResponse(
        502,
        "PLATFORM_UPSTREAM_INVALID",
        "The learning service returned an invalid response."
      );
    }
    const responseBody = await upstream.text();
    if (Buffer.byteLength(responseBody, "utf8") > MAX_RESPONSE_BYTES) {
      return errorResponse(
        502,
        "PLATFORM_UPSTREAM_TOO_LARGE",
        "The learning service response exceeded the safety limit."
      );
    }
    const headers = new Headers({
      "cache-control": "no-store",
      "content-type": "application/json; charset=utf-8",
      "x-content-type-options": "nosniff"
    });
    if (accountContext?.created === true) {
      headers.set("set-cookie", accountCookie(accountContext.accountId, request.url));
    }
    return new Response(responseBody, {
      status: upstream.status,
      headers
    });
  } catch {
    return errorResponse(
      503,
      "PLATFORM_UPSTREAM_UNAVAILABLE",
      "The learning service is temporarily unavailable."
    );
  } finally {
    clearTimeout(timeout);
  }
}

function resolveAccountContext(request: Request): Readonly<{
  accountId: string;
  created: boolean;
}> {
  const cookies = parseCookies(request.headers.get("cookie") ?? "");
  const existing = cookies.get(ACCOUNT_COOKIE);
  if (existing !== undefined && ACCOUNT_ID_PATTERN.test(existing)) {
    return { accountId: existing.toLowerCase(), created: false };
  }
  return { accountId: randomUUID().toLowerCase(), created: true };
}

function parseCookies(value: string): ReadonlyMap<string, string> {
  const parsed = new Map<string, string>();
  for (const entry of value.split(";")) {
    const separator = entry.indexOf("=");
    if (separator <= 0) {
      continue;
    }
    const name = entry.slice(0, separator).trim();
    const cookieValue = entry.slice(separator + 1).trim();
    if (name !== "" && cookieValue !== "") {
      parsed.set(name, cookieValue);
    }
  }
  return parsed;
}

function accountCookie(accountId: string, requestUrl: string): string {
  const secure = new URL(requestUrl).protocol === "https:" ? "; Secure" : "";
  return `${ACCOUNT_COOKIE}=${accountId}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax${secure}`;
}

function errorResponse(status: number, code: string, message: string): Response {
  return Response.json(
    { detail: { code, message } },
    {
      status,
      headers: {
        "cache-control": "no-store",
        "x-content-type-options": "nosniff"
      }
    }
  );
}
