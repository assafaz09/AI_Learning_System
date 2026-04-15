const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN_KEY = "access_token";

type TokenPayload = { access_token: string };
let refreshInFlight: Promise<boolean> | null = null;

export function getToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(ACCESS_TOKEN_KEY) || "";
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

async function tryRefreshToken(): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const response = await fetch(`${baseUrl}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });

    if (!response.ok) {
      clearAccessToken();
      return false;
    }

    const payload = (await response.json()) as TokenPayload;
    setAccessToken(payload.access_token);
    return true;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

async function authorizedFetch(path: string, options: RequestInit = {}, canRetry = true): Promise<Response> {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, { ...options, headers, credentials: "include" });
  if (response.status !== 401 || !canRetry || path === "/auth/refresh") {
    return response;
  }

  const refreshed = await tryRefreshToken();
  if (!refreshed) {
    return response;
  }

  const retryHeaders = new Headers(options.headers || {});
  const retryToken = getToken();
  if (retryToken) {
    retryHeaders.set("Authorization", `Bearer ${retryToken}`);
  }
  return fetch(`${baseUrl}${path}`, { ...options, headers: retryHeaders, credentials: "include" });
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const response = await authorizedFetch(path, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed ${response.status}`);
  }
  const text = await response.text();
  if (!text) {
    return null as T;
  }
  return JSON.parse(text) as T;
}

export async function uploadFile(path: string, file: File): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  const response = await authorizedFetch(path, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const text = await response.text();
  if (!text) {
    return null;
  }
  return JSON.parse(text);
}

export async function uploadFiles(path: string, files: File[]): Promise<unknown[]> {
  const results: unknown[] = [];
  for (const file of files) {
    const response = await uploadFile(path, file);
    results.push(response);
  }
  return results;
}
