const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem("access_token") || "";
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
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
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    body: form,
    headers
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
