import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import GroupLearningPage from "../app/group-learning/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() })
}));

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...rest }: { children: ReactNode; href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  )
}));

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path === "/documents") return [];
    if (path === "/documents/selected") return { document_ids: [] };
    return null;
  }),
  createGroupLearningSession: vi.fn(),
  errorMessage: (e: unknown, f: string) => (e instanceof Error ? e.message : f),
  getGroupLearningMessages: vi.fn(),
  listGroupLearningSessions: vi.fn(async () => []),
  postGroupLearningMessage: vi.fn(),
  uploadFiles: vi.fn()
}));

describe("GroupLearningPage", () => {
  afterEach(() => cleanup());

  test("renders title and group learning description", async () => {
    render(<GroupLearningPage />);
    expect(await screen.findByRole("heading", { name: /למידה בקבוצה/i })).toBeTruthy();
    expect(screen.getByText(/סוכנים \(מתחיל ובינוני\)/i)).toBeTruthy();
    expect(screen.getByText(/שיחות שמורות/i)).toBeTruthy();
    expect(screen.getByRole("log", { name: /שיחת קבוצה/i })).toBeTruthy();
  });
});
