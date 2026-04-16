import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import QuizPage from "../app/quiz/page";
import { apiFetch } from "../lib/api";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock })
}));

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn()
}));

describe("QuizPage", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
    pushMock.mockReset();
    localStorage.clear();
  });

  test("shows fullscreen loader and then CTA to self-test page", async () => {
    let resolveGenerate: ((value: unknown) => void) | null = null;
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path === "/documents") {
        return [{ id: 1, name: "doc.txt" }];
      }
      if (path === "/quiz/generate") {
        return await new Promise((resolve) => {
          resolveGenerate = resolve;
        });
      }
      return {};
    });

    render(<QuizPage />);
    await screen.findByText("doc.txt");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "צור שאלון" }));

    expect(screen.getByText("מחולל השאלות עובד עכשיו")).toBeDefined();

    resolveGenerate?.({ id: 77, title: "qz", questions: [{ id: 10, prompt: "q" }] });
    await waitFor(() => expect(screen.getByText("מעבר ל-בחן את עצמך")).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "מעבר ל-בחן את עצמך" }));
    expect(pushMock).toHaveBeenCalledWith("/grader");
  });
});
