import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchDoctorHealth } from "./api";

describe("fetchDoctorHealth", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the Firebase ID token as a bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        service: "twinbean-api",
        status: "ok",
        authorization: "doctor",
        uid: "demo-doctor",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchDoctorHealth("firebase-token");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/health/authenticated",
      { headers: { Authorization: "Bearer firebase-token" } },
    );
  });

  it("surfaces the backend authorization message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ detail: "Doctor access is required." }),
      }),
    );

    await expect(fetchDoctorHealth("wrong-role")).rejects.toThrow(
      "Doctor access is required.",
    );
  });
});
