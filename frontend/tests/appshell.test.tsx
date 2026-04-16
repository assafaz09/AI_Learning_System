import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

let mockPathname = "/dashboard";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, ...rest }: any) => <a {...rest}>{children}</a>,
}));

import AppShell from "../components/AppShell";

function makeJwt(email: string): string {
  const header = btoa(JSON.stringify({ alg: "HS256" }));
  const payload = btoa(JSON.stringify({ sub: email, type: "access", exp: 9999999999 }));
  return `${header}.${payload}.sig`;
}

describe("AppShell greeting", () => {
  beforeEach(() => {
    mockPathname = "/dashboard";
    localStorage.setItem("access_token", makeJwt("assaf@example.com"));
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  test("greeting matches Israel time of day", () => {
    render(<AppShell><div>child</div></AppShell>);
    const el = document.querySelector(".sidebar-greeting");
    expect(el).toBeTruthy();
    const text = el!.textContent || "";
    const valid = ["בוקר טוב", "צהריים טובים", "ערב טוב", "לילה טוב"];
    expect(valid.some((g) => text.includes(g))).toBe(true);
  });

  test("does not show greeting on public pages", () => {
    mockPathname = "/login";
    localStorage.clear();
    render(<AppShell><div>child</div></AppShell>);
    expect(document.querySelector(".sidebar-greeting")).toBeNull();
  });
});
