import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import TeacherPage from "../app/teacher/page";

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path === "/documents") {
      return [{ id: 1, name: "doc1.txt" }];
    }
    if (path === "/documents/selected") {
      return { document_ids: [1] };
    }
    return {};
  }),
  uploadFiles: vi.fn(async () => []),
}));

describe("TeacherPage", () => {
  test("shows multi-file upload and selected document", async () => {
    const { container } = render(<TeacherPage />);
    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).toBeTruthy();
    expect(fileInput?.hasAttribute("multiple")).toBe(true);
    expect(await screen.findByText("doc1.txt")).toBeDefined();
  });
});
