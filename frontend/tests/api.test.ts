import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { apiFetch, clearAccessToken, getToken, setAccessToken } from "../lib/api";

describe("api auth refresh flow", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("retries request after 401 using refresh endpoint", async () => {
    setAccessToken("expired-token");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("unauthorized", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "new-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    const data = await apiFetch<{ ok: boolean }>("/documents");
    expect(data.ok).toBe(true);
    expect(getToken()).toBe("new-token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toContain("/auth/refresh");
  });

  test("clears token when refresh fails", async () => {
    setAccessToken("expired-token");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("unauthorized", { status: 401 }))
      .mockResolvedValueOnce(new Response("refresh failed", { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/documents")).rejects.toThrow();
    expect(getToken()).toBe("");
  });

  test("clearAccessToken removes stored token", () => {
    setAccessToken("something");
    clearAccessToken();
    expect(getToken()).toBe("");
  });
});
