import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import TeacherPage from "../app/teacher/page";
import {
  apiFetch,
  deleteDocument,
  getConversationMessages,
  streamTeacherChat,
  getPodcastList,
  streamPodcastGeneration,
  fetchPodcastAudioBlob,
  suggestLearningProjects
} from "../lib/api";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush })
}));

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...rest }: { children: ReactNode; href: string }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  deleteDocument: vi.fn(async () => undefined),
  errorMessage: (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback,
  getConversationMessages: vi.fn(async () => ({
    conversation_id: 10,
    messages: [
      { id: 1, role: "user", content: "מה במסמך?", created_at: "2026-04-15T10:00:00" },
      { id: 2, role: "assistant", content: "יש בו הסבר על גרדיאנט.", created_at: "2026-04-15T10:00:01" }
    ]
  })),
  streamTeacherChat: vi.fn(async (_payload: unknown, handlers: { onDelta: (d: string) => void; onDone: (id: number) => void }) => {
    handlers.onDelta("תשובה");
    handlers.onDelta(" דינמית");
    handlers.onDone(10);
  }),
  uploadFiles: vi.fn(async () => []),
  getPodcastList: vi.fn(async () => []),
  streamPodcastGeneration: vi.fn(async () => undefined),
  fetchPodcastAudioBlob: vi.fn(async () => new Blob([new Uint8Array([0xff, 0xf3])], { type: "audio/mpeg" })),
  suggestLearningProjects: vi.fn(async () => ({
    suggestions: "## פרויקט לדוגמה\nתיאור קצר של הרעיון."
  }))
}));

function setupMocks() {
  const mockedApiFetch = vi.mocked(apiFetch);
  mockedApiFetch.mockReset();
  mockedApiFetch.mockImplementation(async (path: string) => {
    if (path === "/documents") {
      return [{ id: 1, name: "doc1.txt" }];
    }
    if (path === "/documents/selected") {
      return { document_ids: [1] };
    }
    if (path === "/history") {
      return { conversations: [{ id: 10, title: "שיחה ראשונה", created_at: "2026-04-15T10:00:00" }] };
    }
    if (path === "/teacher/chat") {
      return { conversation_id: 10, answer: "תשובה מהמורה" };
    }
    return {};
  });
  vi.mocked(deleteDocument).mockClear();
  vi.mocked(getConversationMessages).mockClear();
  vi.mocked(streamTeacherChat).mockClear();
  vi.mocked(getPodcastList).mockClear();
  vi.mocked(getPodcastList).mockResolvedValue([]);
  vi.mocked(streamPodcastGeneration).mockClear();
  vi.mocked(fetchPodcastAudioBlob).mockClear();
  vi.mocked(suggestLearningProjects).mockClear();
  vi.mocked(suggestLearningProjects).mockResolvedValue({
    suggestions: "## פרויקט לדוגמה\nתיאור קצר של הרעיון."
  });
  mockPush.mockClear();
  sessionStorage.clear();
}

describe("TeacherPage", () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanup();
  });

  test("renders chat layout and loads conversation messages", async () => {
    const { container } = render(<TeacherPage />);
    expect(container.querySelector(".teacher-docs-rail")).toBeTruthy();
    expect(container.querySelector(".teacher-tools-rail")).toBeTruthy();
    expect(container.querySelector(".teacher-chat-main")).toBeTruthy();
    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).toBeTruthy();
    expect(fileInput?.hasAttribute("multiple")).toBe(true);

    expect(await screen.findByText(/doc1\.txt/)).toBeDefined();
    const conversationButton = await screen.findByRole("button", { name: "שיחה ראשונה" });
    fireEvent.click(conversationButton);

    await screen.findByText("מה במסמך?");
    await screen.findByText("יש בו הסבר על גרדיאנט.");
    expect(vi.mocked(getConversationMessages)).toHaveBeenCalledWith(10);
  });

  test("streams assistant response and disables input while sending", async () => {
    const { container } = render(<TeacherPage />);

    const conversationButton = await screen.findByRole("button", { name: "שיחה ראשונה" });
    fireEvent.click(conversationButton);
    await screen.findByText("מה במסמך?");

    let releaseStream: (() => void) | null = null;
    vi.mocked(streamTeacherChat).mockImplementationOnce(
      async (_payload, handlers) =>
        new Promise<void>((resolve) => {
          releaseStream = () => {
            handlers.onDelta("תשובה דינמית");
            handlers.onDone(10);
            resolve();
          };
        })
    );

    const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "תסכם את הפרק" } });
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    fireEvent.click(submitBtn);

    await waitFor(() => expect(vi.mocked(streamTeacherChat)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(streamTeacherChat)).toHaveBeenCalledWith(
      {
        message: "תסכם את הפרק",
        document_ids: [1],
        conversation_id: 10
      },
      expect.objectContaining({
        onDelta: expect.any(Function),
        onDone: expect.any(Function),
        onError: expect.any(Function)
      })
    );

    expect(textarea.disabled).toBe(true);
    releaseStream?.();
    await screen.findByText("תשובה דינמית");
    expect(textarea.disabled).toBe(false);
  });

  test("deletes document and refreshes data", async () => {
    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    fireEvent.click(screen.getByRole("button", { name: "מחיקה" }));

    await waitFor(() => {
      expect(vi.mocked(deleteDocument)).toHaveBeenCalledWith(1);
    });
  });

  test("shows progress indicator and disables input while importing", async () => {
    let resolveImport!: (value: unknown) => void;
    vi.mocked(apiFetch).mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/documents/import-url" && options?.method === "POST") {
        return new Promise((resolve) => { resolveImport = resolve; });
      }
      if (path === "/documents") return [{ id: 1, name: "doc1.txt" }];
      if (path === "/documents/selected") return { document_ids: [1] };
      if (path === "/history") return { conversations: [] };
      return {};
    });

    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    const urlInput = screen.getByPlaceholderText("הדביקו קישור YouTube או אתר אינטרנט");
    fireEvent.change(urlInput, { target: { value: "https://www.youtube.com/watch?v=test" } });
    fireEvent.click(screen.getByRole("button", { name: "ייבוא מקור חיצוני" }));

    await waitFor(() => {
      expect(screen.getByText("מתחבר למקור...")).toBeDefined();
    });
    expect(screen.getByText("מייבא...")).toBeDefined();
    expect((urlInput as HTMLInputElement).disabled).toBe(true);

    resolveImport({ id: 2, name: "YouTube:test", source_type: "youtube" });

    await waitFor(() => {
      expect(screen.getByText("המקור החיצוני נוסף בהצלחה.")).toBeDefined();
    });
    expect((urlInput as HTMLInputElement).disabled).toBe(false);
  });

  test("shows podcast generate button and opens modal on click", async () => {
    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    fireEvent.click(screen.getByRole("tab", { name: "פודקאסט" }));
    const podcastBtn = screen.getByRole("button", { name: "צור פודקאסט" });
    expect(podcastBtn).toBeDefined();
    fireEvent.click(podcastBtn);

    await screen.findByText("בחר מסמכים לפודקאסט");
  });

  test("podcast modal shows documents with checkboxes", async () => {
    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    fireEvent.click(screen.getByRole("tab", { name: "פודקאסט" }));
    fireEvent.click(screen.getByRole("button", { name: "צור פודקאסט" }));
    await screen.findByText("בחר מסמכים לפודקאסט");

    const cancelBtn = screen.getByRole("button", { name: "ביטול" });
    expect(cancelBtn).toBeDefined();
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByText("בחר מסמכים לפודקאסט")).toBeNull();
    });
  });

  test("project ideas tab submits and shows suggestions", async () => {
    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    fireEvent.click(screen.getByRole("tab", { name: "הצעות לפרויקטים" }));

    const focusArea = screen.getByPlaceholderText("נושא מהחומר, מיומנות, או סוג פרויקט...");
    fireEvent.change(focusArea, { target: { value: "למידת בסיסי נתונים" } });

    fireEvent.click(screen.getByRole("button", { name: "הצע פרויקטים" }));

    await waitFor(() => {
      expect(vi.mocked(suggestLearningProjects)).toHaveBeenCalledWith({
        learning_focus: "למידת בסיסי נתונים",
        experience_band: "beginner_short",
        document_ids: [1]
      });
    });
    expect(await screen.findByRole("heading", { name: "פרויקט לדוגמה" })).toBeDefined();
    expect(screen.getByText(/תיאור קצר של הרעיון/)).toBeDefined();
    expect(screen.getByText(/לעבור לעמוד/)).toBeDefined();
  });

  test("project ideas transfer stores draft and navigates", async () => {
    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);

    fireEvent.click(screen.getByRole("tab", { name: "הצעות לפרויקטים" }));
    const focusArea = screen.getByPlaceholderText("נושא מהחומר, מיומנות, או סוג פרויקט...");
    fireEvent.change(focusArea, { target: { value: "נושא לשמירה" } });
    fireEvent.click(screen.getByRole("button", { name: "הצע פרויקטים" }));
    await screen.findByRole("heading", { name: "פרויקט לדוגמה" });

    fireEvent.click(screen.getByRole("button", { name: "כן, מעבר לעמוד פרויקטים שלי" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/teacher/my-projects");
    });
    const raw = sessionStorage.getItem("teacherLearningProjectDraft");
    expect(raw).toBeTruthy();
    const draft = JSON.parse(raw as string) as { document_ids: number[]; learning_focus: string };
    expect(draft.document_ids).toEqual([1]);
    expect(draft.learning_focus).toBe("נושא לשמירה");
  });

  test("shows previous podcasts when available", async () => {
    vi.mocked(getPodcastList).mockResolvedValueOnce([
      { id: 1, title: "פודקאסט — 1 מסמכים", duration_seconds: 320, created_at: "2026-04-15T10:00:00" }
    ]);

    render(<TeacherPage />);
    await screen.findByText(/doc1\.txt/);
    fireEvent.click(screen.getByRole("tab", { name: "פודקאסט" }));
    await screen.findByText(/פודקאסט — 1 מסמכים/);
    expect(screen.getByText(/5:20/)).toBeDefined();
  });
});
