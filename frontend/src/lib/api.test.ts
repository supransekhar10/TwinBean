import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchDoctorDashboard, fetchDoctorHealth, fetchPatientTwin } from "./api";

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

describe("fetchPatientTwin", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("loads detail, rule, and prediction as separate protected resources", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await fetchPatientTwin("tbp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "doctor-token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const call of fetchMock.mock.calls) expect(call[1]).toEqual({ headers: { Authorization: "Bearer doctor-token" } });
  });
});

describe("fetchDoctorDashboard", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("uses one bounded authenticated dashboard request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await fetchDoctorDashboard("doctor-token");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/dashboard/patients?limit=100", { headers: { Authorization: "Bearer doctor-token" } });
  });
  it("preserves authorization status without exposing backend payloads", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    await expect(fetchDoctorDashboard("wrong-role")).rejects.toMatchObject({ status: 403, message: "Patient dashboard could not be loaded." } satisfies Partial<ApiError>);
  });
});
