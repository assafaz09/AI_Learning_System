import { render, screen } from "@testing-library/react";
import DashboardPage from "../app/dashboard/page";
import { describe, expect, test } from "vitest";

describe("DashboardPage", () => {
  test("shows product title", () => {
    render(<DashboardPage />);
    expect(screen.getByText("מערכת הלמידה שלכם")).toBeDefined();
  });
});
