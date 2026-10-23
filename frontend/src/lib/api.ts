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
  latest_review_at?: string | null;
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

export type ReviewNote = { note_id: string; patient_id: string; author_uid: string; text: string; created_at: string };
export type TwiniMessage = { role: "user" | "assistant"; content: string };
export type TwiniResponse = {
  answer: string;
  citations: Array<{ source: string; label: string }>;
  patient_context_used: boolean;
  disclaimer: string;
};

export type AkiPrediction =
  | (Extract<DashboardPrediction, { status: "unavailable" }>)
  | (Extract<DashboardPrediction, { status: "available" }> & {
      attributions: Array<{ feature: string; value: number; expected_value: number; shap_margin: number; semantics: string }>;
    });

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const requestTimeoutMs = 8_000;
const accessCheckTimeoutMs = 2_500;

export function resolveApiBaseUrl(configuredUrl: string, browserHostname?: string): string {
  if (!browserHostname || ["localhost", "127.0.0.1"].includes(browserHostname)) return configuredUrl;
  try {
    const url = new URL(configuredUrl);
    if (["localhost", "127.0.0.1"].includes(url.hostname)) {
      url.hostname = browserHostname;
      return url.origin;
    }
  } catch {
    return configuredUrl;
  }
  return configuredUrl;
}

function getApiBaseUrl(): string {
  return resolveApiBaseUrl(configuredApiBaseUrl, typeof window === "undefined" ? undefined : window.location.hostname);
}

async function fetchWithTimeout(path: string, idToken: string, timeoutMs = requestTimeoutMs): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${getApiBaseUrl()}${path}`, {
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
  const response = await fetchWithTimeout("/health/authenticated", idToken, accessCheckTimeoutMs);

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? `Health check failed (${response.status}).`);
  }

  return response.json() as Promise<DoctorHealth>;
}

export async function askTwini(question: string, patientId: string | null, history: TwiniMessage[], idToken: string): Promise<TwiniResponse> {
  const response = await fetch(`${getApiBaseUrl()}/assistant/chat`, {
    method: "POST",
    headers: { Authorization: `Bearer ${idToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ question, patient_id: patientId, history: history.slice(-10) }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? "Twini could not answer right now.");
  }
  return response.json() as Promise<TwiniResponse>;
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

export async function fetchReviewNotes(patientId: string, idToken: string): Promise<ReviewNote[]> {
  return fetchProtected<ReviewNote[]>(`/patients/${encodeURIComponent(patientId)}/review-notes?limit=20`, idToken);
}

export async function createReviewNote(patientId: string, text: string, idToken: string): Promise<ReviewNote> {
  const response = await fetch(`${getApiBaseUrl()}/patients/${encodeURIComponent(patientId)}/review-notes`, { method: "POST", headers: { Authorization: `Bearer ${idToken}`, "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  if (!response.ok) throw new ApiError(response.status, "Review note could not be saved.");
  return response.json() as Promise<ReviewNote>;
}

export async function downloadPatientReport(patientId: string, idToken: string): Promise<Blob> {
  const response = await fetchWithTimeout(`/patients/${encodeURIComponent(patientId)}/report.pdf`, idToken);
  if (!response.ok) throw new ApiError(response.status, "Patient report could not be generated.");
  return response.blob();
}
