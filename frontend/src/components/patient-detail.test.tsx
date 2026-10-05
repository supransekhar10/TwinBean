import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { PatientDetailView } from "./patient-detail";

vi.mock("recharts", () => ({ CartesianGrid: () => null, Line: () => null, LineChart: ({ children }: { children: unknown }) => children, ResponsiveContainer: ({ children }: { children: unknown }) => children, Tooltip: () => null, XAxis: () => null, YAxis: () => null }));
vi.mock("../lib/firebase", () => ({ firebaseAuth: {} }));

const detail = { patient: { patient_id: "tbp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", display_name: "Synthetic Patient", age: 68, ckd_stage: "G3b" }, ehr_history: [{ event_id: "ehr-1", event_type: "laboratory", event_time: "2026-10-05T08:00:00Z", data: { test_name: "creatinine", value: 2.1, unit: "mg/dL" } }], iot_observations: [{ observation_id: "iot-1", measurement_type: "blood_pressure", observed_at: "2026-10-05T08:00:00Z", data: { systolic: 142, diastolic: 84, unit: "mmHg" } }] };

describe("PatientDetailView", () => {
  it("renders all evidence concepts in separate labelled sections", () => {
    const html = renderToStaticMarkup(<PatientDetailView data={{ detail, rule: null, prediction: null }} />);
    for (const label of ["Synthetic EHR history", "Simulated medical-IoT trends", "Current clinical rule", "24-hour AKI prediction", "SHAP feature influence", "Risk unavailable"]) expect(html).toContain(label);
    expect(html).not.toContain("0%");
  });
});
