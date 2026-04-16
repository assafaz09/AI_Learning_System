const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN_KEY = "access_token";

type TokenPayload = { access_token: string };
let refreshInFlight: Promise<boolean> | null = null;
export type TeacherMessage = { id: number; role: "user" | "assistant"; content: string; created_at: string };
export type TeacherConversationMessagesResponse = { conversation_id: number; messages: TeacherMessage[] };
export type TeacherChatStreamRequest = { message: string; document_ids: number[]; conversation_id?: number | null };
type TeacherStreamHandlers = {
  onDelta: (delta: string) => void;
  onDone: (conversationId: number) => void;
  onError: (detail: string) => void;
};

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

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

async function readErrorDetail(response: Response): Promise<string> {
  const body = await response.text();
  if (!body) {
    return `Request failed ${response.status}`;
  }
  try {
    const parsed = JSON.parse(body) as { detail?: string };
    if (parsed?.detail) {
      return parsed.detail;
    }
  } catch {
    // keep raw body when backend returns non-JSON content
  }
  return body;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const response = await authorizedFetch(path, { ...options, headers });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
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
    throw new Error(await readErrorDetail(response));
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

export async function deleteDocument(documentId: number): Promise<void> {
  const response = await authorizedFetch(`/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
}

export async function getConversationMessages(conversationId: number): Promise<TeacherConversationMessagesResponse> {
  return apiFetch<TeacherConversationMessagesResponse>(`/teacher/conversations/${conversationId}/messages`);
}

export async function streamTeacherChat(
  payload: TeacherChatStreamRequest,
  handlers: TeacherStreamHandlers
): Promise<void> {
  const response = await authorizedFetch("/teacher/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok || !response.body) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || `Streaming request failed ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let activeEvent = "";

  const processBlock = (block: string) => {
    const lines = block.split("\n");
    let data = "";
    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (line.startsWith("event:")) {
        activeEvent = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        data += line.slice("data:".length).trim();
      }
    }
    if (!data) {
      return;
    }
    try {
      const parsed = JSON.parse(data) as { delta?: string; detail?: string; conversation_id?: number };
      if (activeEvent === "delta" && parsed.delta) {
        handlers.onDelta(parsed.delta);
      } else if (activeEvent === "error") {
        handlers.onError(parsed.detail || "Streaming error");
      } else if (activeEvent === "done" && parsed.conversation_id) {
        handlers.onDone(parsed.conversation_id);
      }
    } catch {
      handlers.onError("Failed to parse stream event");
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const block = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      processBlock(block);
      separatorIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim().length > 0) {
        processBlock(buffer);
      }
      break;
    }
  }
}
