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
  patient: { patient_id: string; display_name: string; age: number; sex?: string | null; ckd_stage: string; ckd_context?: string | null };
  current_rule: DashboardClinicalRule | null;
  prediction: DashboardPrediction;
  sessionDraft?: boolean;
};

export type PatientDetail = {
  patient: DashboardPatient["patient"];
  ehr_history: Array<{ event_id: string; event_type: string; event_time: string; data: Record<string, string | number> }>;
  iot_observations: Array<{ observation_id: string; measurement_type: string; observed_at: string; data: Record<string, string | number> }>;
};

export type ClinicalRuleResult = DashboardClinicalRule & {
  evidence: Array<{ event_id: string; observed_at: string; value_mg_dl: number }>;
  criteria_met: string[];
  limitation: string;
};

export type AkiPrediction =
  | (Extract<DashboardPrediction, { status: "unavailable" }>)
  | (Extract<DashboardPrediction, { status: "available" }> & {
      attributions: Array<{ feature: string; value: number; shap_margin: number; semantics: string }>;
    });

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const requestTimeoutMs = 8_000;

async function fetchWithTimeout(path: string, idToken: string): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
  try {
    return await fetch(`${apiBaseUrl}${path}`, {
      headers: { Authorization: `Bearer ${idToken}` },
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError(504, "Patient data request timed out. Please retry shortly.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchDoctorHealth(idToken: string): Promise<DoctorHealth> {
  const response = await fetchWithTimeout("/health/authenticated", idToken);

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? `Health check failed (${response.status}).`);
  }

  return response.json() as Promise<DoctorHealth>;
}

export async function fetchDoctorDashboard(idToken: string, refresh = false): Promise<DashboardPatient[]> {
  const response = await fetchWithTimeout(`/dashboard/patients?limit=100${refresh ? "&refresh=true" : ""}`, idToken);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? "Patient dashboard could not be loaded.");
  }
  return response.json() as Promise<DashboardPatient[]>;
}

async function fetchProtected<T>(path: string, idToken: string): Promise<T> {
  const response = await fetchWithTimeout(path, idToken);
  if (!response.ok) throw new ApiError(response.status, "Patient detail could not be loaded.");
  return response.json() as Promise<T>;
}

export async function fetchPatientTwin(patientId: string, idToken: string) {
  const encodedId = encodeURIComponent(patientId);
  const [detail, rules, predictions] = await Promise.all([
    fetchProtected<PatientDetail>(`/patients/${encodedId}`, idToken),
    fetchProtected<ClinicalRuleResult[]>(`/patients/${encodedId}/clinical-rules?limit=1`, idToken),
    fetchProtected<AkiPrediction[]>(`/patients/${encodedId}/aki-predictions?limit=1`, idToken),
  ]);
  return { detail, rule: rules[0] ?? null, prediction: predictions[0] ?? null };
}
