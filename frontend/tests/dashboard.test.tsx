import { render, screen } from "@testing-library/react";
import DashboardPage from "../app/dashboard/page";
import { describe, expect, test } from "vitest";

describe("DashboardPage", () => {
  test("shows product title", () => {
    render(<DashboardPage />);
    expect(screen.getByText("מערכת הלמידה שלכם")).toBeDefined();
  });

  test("shows three quick action links", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("link", { name: "פתיחת סוכן מורה" })).toBeDefined();
    expect(screen.getByRole("link", { name: "יצירת שאלון חדש" })).toBeDefined();
    expect(screen.getByRole("link", { name: "בחן את עצמך" })).toBeDefined();
  });
});
