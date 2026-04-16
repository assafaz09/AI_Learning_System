import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import HistoryPage from "../app/history/page";

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path === "/history") {
      return {
        conversations: [{ id: 1, title: "שיחה ארוכה עם שם מאוד מאוד ארוך שצריך להיחתך ויזואלית", created_at: "2026-01-01T10:00:00Z" }],
        quizzes: [{ id: 2, title: "שאלון בנושא רשתות נוירונים", created_at: "2026-01-02T10:00:00Z" }],
        grades: [{ id: 3, quiz_id: 2, score: 92, created_at: "2026-01-03T10:00:00Z" }]
      };
    }
    return { conversations: [], quizzes: [], grades: [] };
  })
}));

describe("HistoryPage", () => {
  test("renders readable grouped history sections", async () => {
    render(<HistoryPage />);

    expect(await screen.findByText("היסטוריה")).toBeDefined();
    expect(await screen.findByText("שיחות")).toBeDefined();
    expect(await screen.findByText("שאלונים")).toBeDefined();
    expect(await screen.findByText("ציונים")).toBeDefined();
    expect(await screen.findByText(/שאלון #2/)).toBeDefined();
  });
});
