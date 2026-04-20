import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import MyProjectsPage from "../app/teacher/my-projects/page";
import { createSavedProject, listSavedProjects } from "../lib/api";

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...rest }: { children: ReactNode; href: string }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

vi.mock("../lib/api", () => ({
  errorMessage: (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback,
  createSavedProject: vi.fn(),
  deleteSavedProject: vi.fn(async () => undefined),
  listSavedProjects: vi.fn(async () => []),
  updateSavedProject: vi.fn()
}));

const sampleProject = {
  id: 1,
  kind: "manual" as const,
  title: "פרויקט בדיקה",
  suggestions_body: "",
  learning_focus: "",
  experience_band: "manual",
  document_ids: [] as number[],
  importance: "high" as const,
  description: "תיאור הבדיקה",
  status: "in_progress" as const,
  notes: null,
  created_at: "2026-04-19T12:00:00",
  updated_at: "2026-04-19T12:00:00"
};

describe("MyProjectsPage", () => {
  beforeEach(() => {
    vi.mocked(listSavedProjects).mockResolvedValue([sampleProject]);
    vi.mocked(createSavedProject).mockClear();
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  test("loads projects and shows manual add form", async () => {
    render(<MyProjectsPage />);
    expect(await screen.findByDisplayValue("פרויקט בדיקה")).toBeDefined();
    expect(screen.getByRole("heading", { name: "הוספת פרויקט ידני" })).toBeDefined();
    expect(vi.mocked(listSavedProjects)).toHaveBeenCalled();
  });

  test("submits manual project", async () => {
    vi.mocked(createSavedProject).mockResolvedValueOnce({ ...sampleProject, id: 2 });
    render(<MyProjectsPage />);
    await screen.findByDisplayValue("פרויקט בדיקה");

    const form = document.querySelector(".my-projects-manual-form") as HTMLFormElement;
    const titleInput = form.querySelector('input[type="text"]') as HTMLInputElement;
    const descTa = form.querySelector("textarea") as HTMLTextAreaElement;
    fireEvent.change(titleInput, { target: { value: "Rust" } });
    fireEvent.change(descTa, { target: { value: "ללמוד ownership" } });
    fireEvent.submit(form);

    await waitFor(() => {
      expect(vi.mocked(createSavedProject)).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: "manual",
          title: "Rust",
          description: "ללמוד ownership"
        })
      );
    });
  });
});
