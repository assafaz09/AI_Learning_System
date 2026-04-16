import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import FeedbackPage from "../app/grader/feedback/page";
import { apiFetch } from "../lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({ get: () => "42" })
}));

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn()
}));

describe("FeedbackPage", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  test("shows friendly detailed semantic feedback", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      score: 88,
      feedback: "ציון כולל: 88. ענית נכון רעיונית על רוב השאלות.",
      feedback_items: [
        {
          question_id: 1,
          prompt: "מהי למידת מכונה?",
          your_answer: "מודל שלומד מנתונים",
          expected_core: "למידת מכונה היא שיטה שבה מודל לומד מתבניות בנתונים.",
          why: "התשובה נכונה רעיונית.",
          how_to_improve: "הוסף דוגמה יישומית קצרה.",
          accepted_semantically: true,
          score: 88
        }
      ]
    });

    render(<FeedbackPage />);

    expect(await screen.findByText("המשוב שלך")).toBeDefined();
    expect(await screen.findByText(/הבנת את הרעיון/)).toBeDefined();
    expect(await screen.findByText(/איך לשפר:/)).toBeDefined();
  });
});
