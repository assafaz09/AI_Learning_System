const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN_KEY = "access_token";

type TokenPayload = { access_token: string };
let refreshInFlight: Promise<boolean> | null = null;
export type TeacherMessage = { id: number; role: "user" | "assistant"; content: string; created_at: string };
export type TeacherConversationMessagesResponse = { conversation_id: number; messages: TeacherMessage[] };
export type GroupLearningSession = {
  id: number;
  title: string;
  document_ids: number[];
  next_speaker: string;
};
export type GroupLearningMessage = { id: number; role: string; content: string; created_at: string };
export type GroupLearningMessagesResponse = { session_id: number; messages: GroupLearningMessage[] };
export type GroupLearningReply = { session_id: number; reply: string; speaker: string };
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

export async function listGroupLearningSessions(): Promise<GroupLearningSession[]> {
  return apiFetch<GroupLearningSession[]>("/group-learning/sessions");
}

export async function createGroupLearningSession(body: {
  document_ids: number[];
  title?: string | null;
}): Promise<GroupLearningSession> {
  return apiFetch<GroupLearningSession>("/group-learning/sessions", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function postGroupLearningMessage(sessionId: number, message: string): Promise<GroupLearningReply> {
  return apiFetch<GroupLearningReply>(`/group-learning/sessions/${sessionId}/message`, {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

export async function getGroupLearningMessages(sessionId: number): Promise<GroupLearningMessagesResponse> {
  return apiFetch<GroupLearningMessagesResponse>(`/group-learning/sessions/${sessionId}/messages`);
}

export type PodcastItem = {
  id: number;
  title: string;
  duration_seconds: number;
  created_at: string;
};

type PodcastStreamHandlers = {
  onProgress: (message: string, step?: number, total?: number) => void;
  onDone: (podcastId: number, durationSeconds: number) => void;
  onError: (detail: string) => void;
};

export async function getPodcastList(): Promise<PodcastItem[]> {
  return apiFetch<PodcastItem[]>("/podcast/list");
}

export function getPodcastAudioUrl(podcastId: number): string {
  return `${baseUrl}/podcast/${podcastId}/audio`;
}

/** Use for <audio>: plain GET from src= cannot send Authorization; fetch with token then object URL. */
export async function fetchPodcastAudioBlob(podcastId: number): Promise<Blob> {
  const response = await authorizedFetch(`/podcast/${podcastId}/audio`, { method: "GET" });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.blob();
}

export async function streamPodcastGeneration(
  documentIds: number[],
  handlers: PodcastStreamHandlers
): Promise<void> {
  const response = await authorizedFetch("/podcast/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds }),
  });

  if (!response.ok || !response.body) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || `Podcast generation request failed ${response.status}`);
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
    if (!data) return;
    try {
      const parsed = JSON.parse(data) as {
        message?: string;
        step?: number;
        total?: number;
        detail?: string;
        podcast_id?: number;
        duration_seconds?: number;
      };
      if (activeEvent === "progress" && parsed.message) {
        handlers.onProgress(parsed.message, parsed.step, parsed.total);
      } else if (activeEvent === "error") {
        handlers.onError(parsed.detail || "Podcast generation error");
      } else if (activeEvent === "done" && parsed.podcast_id) {
        handlers.onDone(parsed.podcast_id, parsed.duration_seconds || 0);
      }
    } catch {
      handlers.onError("Failed to parse podcast stream event");
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
      if (buffer.trim().length > 0) processBlock(buffer);
      break;
    }
  }
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

export type ExperienceBand = "beginner_short" | "intermediate_days" | "advanced_extended";

export type ProjectIdeasRequestBody = {
  learning_focus: string;
  experience_band: ExperienceBand;
  document_ids?: number[] | null;
};

export type ProjectIdeasApiResponse = {
  suggestions: string;
};

export async function suggestLearningProjects(body: ProjectIdeasRequestBody): Promise<ProjectIdeasApiResponse> {
  return apiFetch<ProjectIdeasApiResponse>("/teacher/project-ideas", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export type SavedProjectStatus = "not_started" | "in_progress" | "done";
export type ProjectKind = "ai" | "manual";
export type ProjectImportance = "low" | "medium" | "high";

export type SavedProject = {
  id: number;
  kind: ProjectKind;
  title: string;
  suggestions_body: string;
  learning_focus: string;
  experience_band: string;
  document_ids: number[];
  importance: ProjectImportance;
  description: string | null;
  status: SavedProjectStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type SavedProjectCreateBody =
  | {
      kind: "ai";
      title: string;
      suggestions_body: string;
      learning_focus: string;
      experience_band: ExperienceBand;
      document_ids: number[];
    }
  | {
      kind: "manual";
      title: string;
      description: string;
      importance?: ProjectImportance;
      status?: SavedProjectStatus;
    };

export type SavedProjectUpdateBody = {
  title?: string;
  status?: SavedProjectStatus;
  notes?: string;
  importance?: ProjectImportance;
  description?: string | null;
};

export async function listSavedProjects(): Promise<SavedProject[]> {
  return apiFetch<SavedProject[]>("/teacher/saved-projects");
}

export async function createSavedProject(body: SavedProjectCreateBody): Promise<SavedProject> {
  return apiFetch<SavedProject>("/teacher/saved-projects", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function updateSavedProject(id: number, body: SavedProjectUpdateBody): Promise<SavedProject> {
  return apiFetch<SavedProject>(`/teacher/saved-projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

export async function deleteSavedProject(id: number): Promise<void> {
  const response = await authorizedFetch(`/teacher/saved-projects/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
}

export type ProgressSummary = {
  documents_count: number;
  conversations_count: number;
  teacher_messages_count: number;
  quizzes_created: number;
  quizzes_graded: number;
  average_quiz_score: number | null;
  best_quiz_score: number | null;
  group_sessions_count: number;
  group_messages_count: number;
  projects_total: number;
  projects_done: number;
  projects_in_progress: number;
  projects_not_started: number;
  projects_completion_percent: number;
  podcasts_count: number;
  overall_progress_percent: number;
};

export type QuizScorePoint = {
  date: string;
  score: number;
  quiz_id: number;
  quiz_title: string;
};

export type ActivityDay = { date: string; count: number };

export type ActivityBreakdown = {
  teacher_messages: number;
  quiz_submissions: number;
  group_messages: number;
  documents_uploaded: number;
  projects_updated: number;
  podcasts_created: number;
};

export type ProjectStatusSlice = { label: string; value: number; percent: number };

export type ProgressDashboard = {
  summary: ProgressSummary;
  quiz_scores_timeline: QuizScorePoint[];
  activity_last_14_days: ActivityDay[];
  activity_breakdown: ActivityBreakdown;
  project_status_slices: ProjectStatusSlice[];
  insights: string[];
};

export async function fetchProgressDashboard(): Promise<ProgressDashboard> {
  return apiFetch<ProgressDashboard>("/progress");
}
