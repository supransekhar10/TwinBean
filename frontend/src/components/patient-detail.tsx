"use client";

import { onAuthStateChanged, signOut } from "@firebase/auth";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ApiError, fetchPatientTwin, type AkiPrediction, type ClinicalRuleResult, type PatientDetail } from "../lib/api";
import { firebaseAuth } from "../lib/firebase";

type TwinData = { detail: PatientDetail; rule: ClinicalRuleResult | null; prediction: AkiPrediction | null };
const featureLabels: Record<string, string> = { age_years: "Age", latest_creatinine_mg_dl: "Latest creatinine", creatinine_delta_48h_mg_dl: "48-hour creatinine change", latest_systolic_bp_mmhg: "Latest systolic blood pressure" };
const ruleLabels = { criteria_met: "Criteria met", criteria_not_met: "Criteria not met", insufficient_creatinine_history: "Insufficient creatinine history" };

function formatTime(value: string) { return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC"; }
function latestWarning(prediction: AkiPrediction | null) {
  if (!prediction) return "No stored prediction is available.";
  const code = prediction.warnings[0] ?? (prediction.status === "unavailable" ? prediction.reasons[0] : null);
  const known: Record<string, string> = { stale_ehr_observation: "EHR data is stale.", stale_iot_observation: "Simulated IoT data is stale.", missing_iot_observation: "Simulated IoT data is missing.", no_stored_prediction: "No stored prediction is available." };
  return code ? known[code] ?? "Prediction data needs review." : null;
}

export function PatientDetailView({ data }: { data: TwinData }) {
  const creatinine = data.detail.ehr_history.filter((event) => event.event_type === "laboratory" && event.data.test_name === "creatinine").map((event) => ({ time: formatTime(event.event_time), value: Number(event.data.value) }));
  const bloodPressure = data.detail.iot_observations.filter((item) => item.measurement_type === "blood_pressure").map((item) => ({ time: formatTime(item.observed_at), value: Number(item.data.systolic) }));
  const warning = latestWarning(data.prediction);
  return <main className="detail-shell">
    <header className="detail-header"><div><p className="context-label">Synthetic patient digital twin</p><h1>{data.detail.patient.display_name}</h1><p>Age {data.detail.patient.age} / CKD stage {data.detail.patient.ckd_stage}</p></div><div className="detail-actions"><Link className="secondary-button" href="/dashboard">Back to dashboard</Link><button className="text-button" type="button" onClick={() => signOut(firebaseAuth)}>Sign out</button></div></header>
    <p className="prototype-notice">Research prototype / synthetic data only / not for clinical use</p>
    <section className="evidence-section" aria-labelledby="ehr-heading"><h2 id="ehr-heading">Synthetic EHR history</h2><p>Longitudinal clinical records. This stream is separate from simulated IoT observations.</p><div className="chart-frame" aria-label="Creatinine history chart"><ResponsiveContainer width="100%" height={240}><LineChart data={creatinine}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" hide /><YAxis unit=" mg/dL" /><Tooltip /><Line type="monotone" dataKey="value" stroke="#0d665d" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div><ul className="record-list">{data.detail.ehr_history.slice().reverse().map((event) => <li key={event.event_id}><strong>{event.event_type}</strong><span>{formatTime(event.event_time)}</span><span>{String(event.data.test_name ?? event.data.medication ?? event.data.encounter_type ?? "Synthetic record")} {event.data.value !== undefined ? `: ${event.data.value} ${event.data.unit ?? ""}` : ""}</span></li>)}</ul></section>
    <section className="evidence-section" aria-labelledby="iot-heading"><h2 id="iot-heading">Simulated medical-IoT trends</h2><p>Wearable and home-monitoring observations, maintained as a separate time-series stream.</p><div className="chart-frame" aria-label="Systolic blood pressure trend chart"><ResponsiveContainer width="100%" height={240}><LineChart data={bloodPressure}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" hide /><YAxis unit=" mmHg" /><Tooltip /><Line type="monotone" dataKey="value" stroke="#376e9a" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></section>
    <div className="clinical-grid">
      <section className="evidence-section rule-detail" aria-labelledby="rule-heading"><p className="context-label">Observed state</p><h2 id="rule-heading">Current clinical rule</h2><strong>{data.rule ? ruleLabels[data.rule.status] : "Insufficient creatinine history"}</strong><p>{data.rule?.limitation ?? "No stored rule evidence is available."}</p></section>
      <section className="evidence-section prediction-detail" aria-labelledby="prediction-heading"><p className="context-label">Future model output</p><h2 id="prediction-heading">24-hour AKI prediction</h2><strong>{data.prediction?.status === "available" ? `${Math.round(data.prediction.probability * 100)}%` : "Risk unavailable"}</strong><p>Prediction generated: {data.prediction?.generated_at ? formatTime(data.prediction.generated_at) : "Not available"}</p>{warning && <p className="quality-warning"><span className="data-label">Data quality warning</span>{warning}</p>}</section>
    </div>
    <section className="evidence-section" aria-labelledby="shap-heading"><p className="context-label">Explanation / not causal</p><h2 id="shap-heading">SHAP feature influence</h2>{data.prediction?.status === "available" && data.prediction.attributions.length ? <ol className="shap-list">{[...data.prediction.attributions].sort((a, b) => Math.abs(b.shap_margin) - Math.abs(a.shap_margin)).map((item) => <li key={item.feature}><span>{featureLabels[item.feature] ?? item.feature}</span><strong>{item.shap_margin >= 0 ? "+" : ""}{item.shap_margin.toFixed(3)}</strong></li>)}</ol> : <p>Explanation unavailable because there is no valid prediction.</p>}<p>SHAP values describe this model output; they do not establish causation or treatment guidance.</p></section>
  </main>;
}

export function PatientDetailScreen({ patientId }: { patientId: string }) {
  const [state, setState] = useState<"loading" | "ready" | "error" | "unauthorized">("loading");
  const [data, setData] = useState<TwinData | null>(null);
  useEffect(() => onAuthStateChanged(firebaseAuth, async (user) => {
    if (!user) { setState("unauthorized"); return; }
    try { setData(await fetchPatientTwin(patientId, await user.getIdToken())); setState("ready"); }
    catch (error) { setState(error instanceof ApiError && (error.status === 401 || error.status === 403) ? "unauthorized" : "error"); }
  }), [patientId]);
  if (state === "loading") return <main className="detail-shell"><h1>Loading patient digital twin...</h1></main>;
  if (state === "unauthorized") return <main className="detail-shell"><h1>Doctor access is required</h1><p>Sign in with an approved doctor account from the dashboard.</p><Link className="primary-button" href="/">Return to sign in</Link></main>;
  if (state === "error" || !data) return <main className="detail-shell"><h1>Patient detail could not be loaded</h1><p>Check the backend connection and return to the dashboard to retry.</p><Link className="secondary-button" href="/dashboard">Back to dashboard</Link></main>;
  return <PatientDetailView data={data} />;
}
