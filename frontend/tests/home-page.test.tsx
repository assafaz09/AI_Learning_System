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

  test("renders auth links with correct destinations", () => {
    render(<HomePage />);
    expect(screen.getByRole("link", { name: "התחברות" }).getAttribute("href")).toBe("/login");
    expect(screen.getByRole("link", { name: "הרשמה" }).getAttribute("href")).toBe("/register");
  });
});
