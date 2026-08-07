import { randomUUID } from "node:crypto";

import { readApiBaseUrl } from "../../../../server/config/api-base";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const preferredRegion = "pdx1";

const UPSTREAM_TIMEOUT_MS = 8_000;
const TUTOR_UPSTREAM_TIMEOUT_MS = 35_000;
const MAX_REQUEST_BYTES = 96 * 1024;
const MAX_RESPONSE_BYTES = 768 * 1024;
const ACCOUNT_COOKIE = "ai_platform_account";
const ACCOUNT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ACCOUNT_DELETE_PATH = "account";
const TUTOR_STREAM_PATH = "tutor/stream";
const ALLOWED_PATHS = new Set([
  "roles",
  "plans",
  "plans/resume",
  "plans/replan",
  "progress",
  "assessments/start",
  "assessments/submit",
  ACCOUNT_DELETE_PATH,
  TUTOR_STREAM_PATH
]);

const GET_PATHS = new Set(["roles"]);
const DELETE_PATHS = new Set([ACCOUNT_DELETE_PATH]);

type RouteContext = Readonly<{
  params: Promise<Readonly<{ path: string[] }>>;
}>;

type ProxyMethod = "DELETE" | "GET" | "POST";
type AccountContext = Readonly<{ accountId: string; created: boolean }>;

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

export async function DELETE(
  request: Request,
  context: RouteContext
): Promise<Response> {
  return proxyRequest(request, context, "DELETE");
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
  if (!methodAllowed(relativePath, method)) {
    return errorResponse(405, "PLATFORM_METHOD_NOT_ALLOWED", "The request method is not allowed.");
  }

  const isAccountDeletion = relativePath === ACCOUNT_DELETE_PATH && method === "DELETE";
  const accountContext =
    method === "GET"
      ? null
      : isAccountDeletion
        ? resolveExistingAccountContext(request)
        : resolveAccountContext(request);

  if (isAccountDeletion && accountContext === null) {
    const headers = responseHeaders("application/json; charset=utf-8");
    headers.set("set-cookie", expiredAccountCookie(request.url));
    return new Response(
      JSON.stringify({ deleted: false, scope: "current_anonymous_account" }),
      { status: 200, headers }
    );
  }

  let body: string | undefined;
  if (method !== "GET") {
    body = await request.text();
    if (Buffer.byteLength(body, "utf8") > MAX_REQUEST_BYTES) {
      return errorResponse(413, "PLATFORM_REQUEST_TOO_LARGE", "The request is too large.");
    }
  }

  const isTutorStream = relativePath === TUTOR_STREAM_PATH;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    isTutorStream ? TUTOR_UPSTREAM_TIMEOUT_MS : UPSTREAM_TIMEOUT_MS
  );
  try {
    const upstreamUrl = new URL(`/api/v1/${relativePath}`, readApiBaseUrl());
    const upstream = await fetch(upstreamUrl, {
      method,
      headers: {
        accept: isTutorStream ? "text/event-stream" : "application/json",
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

    if (isTutorStream && upstream.ok) {
      if (!contentType.startsWith("text/event-stream") || upstream.body === null) {
        return errorResponse(
          502,
          "PLATFORM_UPSTREAM_INVALID",
          "The tutor service returned an invalid stream."
        );
      }
      const headers = responseHeaders("text/event-stream; charset=utf-8");
      headers.set("x-accel-buffering", "no");
      applyAccountCookie(headers, accountContext, request.url);
      return new Response(upstream.body, {
        status: upstream.status,
        headers
      });
    }

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
    const headers = responseHeaders("application/json; charset=utf-8");
    if (isAccountDeletion && upstream.ok) {
      headers.set("set-cookie", expiredAccountCookie(request.url));
    } else {
      applyAccountCookie(headers, accountContext, request.url);
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

function methodAllowed(relativePath: string, method: ProxyMethod): boolean {
  if (method === "GET") {
    return GET_PATHS.has(relativePath);
  }
  if (method === "DELETE") {
    return DELETE_PATHS.has(relativePath);
  }
  return !GET_PATHS.has(relativePath) && !DELETE_PATHS.has(relativePath);
}

function resolveExistingAccountContext(request: Request): AccountContext | null {
  const cookies = parseCookies(request.headers.get("cookie") ?? "");
  const existing = cookies.get(ACCOUNT_COOKIE);
  if (existing === undefined || !ACCOUNT_ID_PATTERN.test(existing)) {
    return null;
  }
  return { accountId: existing.toLowerCase(), created: false };
}

function resolveAccountContext(request: Request): AccountContext {
  return (
    resolveExistingAccountContext(request) ?? {
      accountId: randomUUID().toLowerCase(),
      created: true
    }
  );
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

function expiredAccountCookie(requestUrl: string): string {
  const secure = new URL(requestUrl).protocol === "https:" ? "; Secure" : "";
  return `${ACCOUNT_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${secure}`;
}

function responseHeaders(contentType: string): Headers {
  return new Headers({
    "cache-control": "no-store",
    "content-type": contentType,
    "x-content-type-options": "nosniff"
  });
}

function applyAccountCookie(
  headers: Headers,
  accountContext: AccountContext | null,
  requestUrl: string
): void {
  if (accountContext?.created === true) {
    headers.set("set-cookie", accountCookie(accountContext.accountId, requestUrl));
  }
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
