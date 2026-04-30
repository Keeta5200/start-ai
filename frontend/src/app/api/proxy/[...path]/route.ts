import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function getBackendBaseUrl() {
  if (process.env.INTERNAL_API_BASE_URL) {
    return process.env.INTERNAL_API_BASE_URL;
  }

  if (process.env.RAILWAY_ENVIRONMENT) {
    return "http://backend.railway.internal:8080/api/v1";
  }

  return "http://127.0.0.1:8000/api/v1";
}

async function proxyRequest(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const upstreamUrl = `${getBackendBaseUrl()}/${path}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
    cache: "no-store"
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstreamResponse = await fetchWithRetry(upstreamUrl, init);
  const responseHeaders = new Headers(upstreamResponse.headers);

  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders
  });
}

async function fetchWithRetry(url: string, init: RequestInit) {
  let lastError: unknown;

  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const response = await fetch(url, init);
      if (!shouldRetryResponse(response.status) || attempt === 4) {
        return response;
      }
    } catch (error) {
      lastError = error;
      if (attempt === 4) {
        throw error;
      }
    }

    await wait(1500 * attempt);
  }

  throw lastError ?? new Error("Upstream request failed");
}

function shouldRetryResponse(status: number) {
  return status === 425 || status === 429 || status === 500 || status === 502 || status === 503 || status === 504;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export {
  proxyRequest as GET,
  proxyRequest as POST,
  proxyRequest as PUT,
  proxyRequest as PATCH,
  proxyRequest as DELETE,
  proxyRequest as OPTIONS
};
