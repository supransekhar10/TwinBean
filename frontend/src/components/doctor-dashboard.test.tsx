import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { DashboardPatient } from "@/lib/api";
import { DoctorDashboard } from "./doctor-dashboard";

const rows: DashboardPatient[] = [
  { patient: { patient_id: "tbp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", display_name: "High Risk", age: 71, ckd_stage: "G4" }, current_rule: { status: "criteria_met", calculation_time: "2026-10-05T08:00:00Z", prediction_cutoff: "2026-10-05T08:00:00Z", insufficiency_reasons: [] }, prediction: { status: "available", probability: 0.82, prediction_cutoff: "2026-10-05T08:00:00Z", generated_at: "2026-10-05T08:01:00Z", warnings: ["iot_data_stale"] } },
  { patient: { patient_id: "tbp-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", display_name: "Unavailable", age: 63, ckd_stage: "G3b" }, current_rule: null, prediction: { status: "unavailable", generated_at: null, reasons: ["no_stored_prediction"], warnings: [] } },
];

describe("DoctorDashboard", () => {
  it("keeps current rules and future risk visibly separate", () => {
    const html = renderToStaticMarkup(<DoctorDashboard rows={rows} />);
    expect(html).toContain("Current clinical rule");
    expect(html).toContain("24-hour AKI risk");
    expect(html).toContain("82%");
    expect(html).toContain("Prediction generated");
    expect(html).toContain("Review now");
    expect(html).toContain("Search patients");
    expect(html).toContain("Alerts off");
    expect(html).not.toContain("Data quality");
    expect(html).not.toContain("Simulated IoT data is stale.");
    expect(html).toContain("Open patient High Risk");
  });
  it("renders unavailable risk exactly without a numeric fallback", () => {
    const html = renderToStaticMarkup(<DoctorDashboard rows={[rows[1]]} />);
    expect(html).toContain("Risk unavailable");
    expect(html).not.toContain("Data quality");
    expect(html).not.toContain("0%");
  });
  it("distinguishes temporary patient-data unavailability from authorization failure", () => {
    const html = renderToStaticMarkup(<DoctorDashboard rows={[]} error="unavailable" />);
    expect(html).toContain("Patient data is temporarily unavailable");
    expect(html).toContain("Firestore could not complete the request");
    expect(html).not.toContain("Doctor access is required");
  });
});
