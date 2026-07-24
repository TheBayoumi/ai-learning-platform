import { readApiBaseUrl } from "../../../../server/config/api-base";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const UPSTREAM_TIMEOUT_MS = 8_000;
const MAX_REQUEST_BYTES = 96 * 1024;
const MAX_RESPONSE_BYTES = 768 * 1024;
const ALLOWED_PATHS = new Set([
  "roles",
  "plans",
  "plans/resume",
  "plans/replan",
  "progress"
]);

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
  if ((relativePath === "roles") !== (method === "GET")) {
    return errorResponse(405, "PLATFORM_METHOD_NOT_ALLOWED", "The request method is not allowed.");
  }

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
        ...(body === undefined ? {} : { "content-type": "application/json" })
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
    return new Response(responseBody, {
      status: upstream.status,
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
        "x-content-type-options": "nosniff"
      }
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
