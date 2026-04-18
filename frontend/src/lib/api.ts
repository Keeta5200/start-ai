import { AnalysisDetail, AnalysisSummary, AuthResponse, LoginPayload } from "@/lib/types";
import { AUTH_TOKEN_COOKIE_NAME } from "@/lib/auth";

function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    return "/api/proxy";
  }

  return process.env.INTERNAL_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
}

async function getAuthHeaders(initHeaders?: HeadersInit): Promise<Headers> {
  const headers = new Headers(initHeaders ?? {});

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("start-ai-token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  }

  const { cookies } = await import("next/headers");
  const token = cookies().get(AUTH_TOKEN_COOKIE_NAME)?.value;
  if (token) {
    headers.set("Authorization", `Bearer ${decodeURIComponent(token)}`);
  }
  return headers;
}

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, detail?: string) {
    super(detail ?? `Request failed: ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await getAuthHeaders(init?.headers);
  if (!headers.has("Content-Type") && init?.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function register(payload: LoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAnalyses(): Promise<AnalysisSummary[]> {
  return request<AnalysisSummary[]>("/analyses");
}

export async function getAnalysis(id: string): Promise<AnalysisDetail> {
  return request<AnalysisDetail>(`/analyses/${id}`);
}
