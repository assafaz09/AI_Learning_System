import type { ExperienceBand } from "./api";

export const TEACHER_PROJECT_DRAFT_STORAGE_KEY = "teacherLearningProjectDraft";

export type TeacherProjectDraft = {
  title: string;
  suggestions_body: string;
  learning_focus: string;
  experience_band: ExperienceBand;
  document_ids: number[];
};

export function splitProjectSuggestions(markdown: string): { title: string; body: string }[] {
  const lines = markdown.split("\n");
  const out: { title: string; body: string }[] = [];
  let curTitle: string | null = null;
  const buf: string[] = [];

  const push = () => {
    if (curTitle === null && buf.length === 0) return;
    const body = buf.join("\n").trim();
    const t = curTitle ?? "פתיחה";
    out.push({ title: t, body: body || "—" });
    buf.length = 0;
  };

  for (const line of lines) {
    if (line.startsWith("## ")) {
      push();
      curTitle = line.slice(3).trim() || "הצעה";
    } else {
      buf.push(line);
    }
  }
  push();

  if (out.length === 0) {
    return [{ title: "הצעות", body: markdown.trim() || "—" }];
  }
  return out;
}

export function defaultSaveTitle(suggestions: string, focus: string): string {
  const m = suggestions.match(/^##\s+(.+)$/m);
  if (m?.[1]) {
    return m[1].trim().slice(0, 255);
  }
  const f = focus.trim();
  if (f.length > 80) {
    return `${f.slice(0, 77)}…`;
  }
  return f || "פרויקט ללא כותרת";
}
