const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export class ApiError extends Error {
  status: number;
  fields: Record<string, unknown>;

  constructor(status: number, message: string, fields: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem("orion_refresh");
  if (!refresh) return null;
  const response = await fetch(`${API_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) {
    localStorage.removeItem("orion_access");
    localStorage.removeItem("orion_refresh");
    return null;
  }
  const data = await response.json();
  localStorage.setItem("orion_access", data.access);
  if (data.refresh) localStorage.setItem("orion_refresh", data.refresh);
  return data.access as string;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const access = localStorage.getItem("orion_access");
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 401 && retry && localStorage.getItem("orion_refresh")) {
    refreshPromise ||= refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
    const nextAccess = await refreshPromise;
    if (nextAccess) return apiRequest<T>(path, options, false);
  }

  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    throw new ApiError(response.status, error?.message || "Network request failed", error?.fields || {});
  }
  return body as T;
}

export { API_URL };
