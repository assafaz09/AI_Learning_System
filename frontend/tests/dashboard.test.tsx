import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "../app/dashboard/page";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mockDashboard = {
  summary: {
    documents_count: 2,
    conversations_count: 3,
    teacher_messages_count: 8,
    quizzes_created: 2,
    quizzes_graded: 2,
    average_quiz_score: 78,
    best_quiz_score: 85,
    group_sessions_count: 1,
    group_messages_count: 4,
    projects_total: 2,
    projects_done: 1,
    projects_in_progress: 1,
    projects_not_started: 0,
    projects_completion_percent: 50,
    podcasts_count: 0,
    overall_progress_percent: 65
  },
  quiz_scores_timeline: [
    { date: "2026-06-10", score: 72, quiz_id: 1, quiz_title: "בוחן 1" },
    { date: "2026-06-15", score: 85, quiz_id: 2, quiz_title: "בוחן 2" }
  ],
  activity_last_14_days: Array.from({ length: 14 }, (_, i) => ({
    date: `2026-06-${String(i + 1).padStart(2, "0")}`,
    count: i % 3
  })),
  activity_breakdown: {
    teacher_messages: 8,
    quiz_submissions: 2,
    group_messages: 4,
    documents_uploaded: 2,
    projects_updated: 2,
    podcasts_created: 0
  },
  project_status_slices: [
    { label: "הושלמו", value: 1, percent: 50 },
    { label: "בתהליך", value: 1, percent: 50 },
    { label: "לא התחילו", value: 0, percent: 0 }
  ],
  insights: ["ממשיכים בקצב טוב — שמרו על שגרת למידה קבועה."]
};

vi.mock("../lib/api", () => ({
  fetchProgressDashboard: vi.fn(() => Promise.resolve(mockDashboard)),
  errorMessage: (_: unknown, fallback: string) => fallback
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("shows progress dashboard title", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("המסע הלימודי שלכם במבט אחד")).toBeDefined();
    });
  });

  test("shows overall progress and stat cards", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("65%")).toBeDefined();
      expect(screen.getByText("ממוצע ציונים")).toBeDefined();
      expect(screen.getByText("78%")).toBeDefined();
    });
  });

  test("shows quick action links", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: "פתיחת סוכן מורה" }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: "למידה בקבוצה" }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: "יצירת שאלון" }).length).toBeGreaterThan(0);
    });
  });
});
