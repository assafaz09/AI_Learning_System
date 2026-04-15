import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import HomePage from "../app/page";

describe("HomePage", () => {
  test("shows product value and auth actions", () => {
    render(<HomePage />);
    expect(screen.getByText("פלטפורמת למידה מבוססת בינה מלאכותית")).toBeDefined();
    expect(screen.getByText("התחברות")).toBeDefined();
    expect(screen.getByText("הרשמה")).toBeDefined();
  });
});
