export type DoctorHealth = {
  service: string;
  status: string;
  authorization: "doctor";
  uid: string;
};

export type DashboardClinicalRule = {
  status: "criteria_met" | "criteria_not_met" | "insufficient_creatinine_history";
  calculation_time: string;
  prediction_cutoff: string;
  insufficiency_reasons: string[];
};

export type DashboardPrediction =
  | { status: "available"; probability: number; prediction_cutoff: string; generated_at: string; warnings: string[] }
  | { status: "unavailable"; prediction_cutoff?: string | null; generated_at?: string | null; reasons: string[]; warnings: string[] };

export type DashboardPatient = {
  patient: { patient_id: string; display_name: string; age: number; ckd_stage: string };
  current_rule: DashboardClinicalRule | null;
  prediction: DashboardPrediction;
};

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchDoctorHealth(idToken: string): Promise<DoctorHealth> {
  const response = await fetch(`${apiBaseUrl}/health/authenticated`, {
    headers: { Authorization: `Bearer ${idToken}` },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Health check failed (${response.status}).`);
  }

  return response.json() as Promise<DoctorHealth>;
}

export async function fetchDoctorDashboard(idToken: string): Promise<DashboardPatient[]> {
  const response = await fetch(`${apiBaseUrl}/dashboard/patients?limit=100`, {
    headers: { Authorization: `Bearer ${idToken}` },
  });
  if (!response.ok) throw new ApiError(response.status, "Patient dashboard could not be loaded.");
  return response.json() as Promise<DashboardPatient[]>;
}
