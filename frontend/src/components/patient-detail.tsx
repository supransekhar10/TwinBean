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
  const egfr = data.detail.ehr_history.filter((event) => event.event_type === "laboratory" && event.data.test_name === "egfr").map((event) => ({ time: formatTime(event.event_time), value: Number(event.data.value) }));
  const bloodPressure = data.detail.iot_observations.filter((item) => item.measurement_type === "blood_pressure").map((item) => ({ time: formatTime(item.observed_at), value: Number(item.data.systolic) }));
  const warning = latestWarning(data.prediction);
  const attributions = data.prediction?.status === "available" ? [...data.prediction.attributions].sort((a, b) => Math.abs(b.shap_margin) - Math.abs(a.shap_margin)) : [];
  const maxInfluence = Math.max(...attributions.map((item) => Math.abs(item.shap_margin)), 0);
  return <main className="detail-shell">
    <header className="detail-header"><div><p className="context-label">Synthetic patient digital twin</p><h1>{data.detail.patient.display_name}</h1><p>Age {data.detail.patient.age}{data.detail.patient.sex ? ` / ${data.detail.patient.sex}` : ""} / CKD stage {data.detail.patient.ckd_stage}</p>{data.detail.patient.ckd_context && <p>{data.detail.patient.ckd_context}</p>}</div><div className="detail-actions"><Link className="secondary-button" href="/dashboard">Back to dashboard</Link><button className="text-button" type="button" onClick={() => signOut(firebaseAuth)}>Sign out</button></div></header>
    <p className="prototype-notice">Research prototype / synthetic data only / not for clinical use</p>
    <div className="metric-grid"><div><span>Latest creatinine</span><strong>{creatinine.at(-1)?.value.toFixed(2) ?? "Unavailable"}</strong><small>mg/dL</small></div><div><span>Latest eGFR</span><strong>{egfr.at(-1)?.value.toFixed(1) ?? "Unavailable"}</strong><small>mL/min/1.73m²</small></div><div><span>Latest systolic BP</span><strong>{bloodPressure.at(-1)?.value.toFixed(0) ?? "Unavailable"}</strong><small>mmHg</small></div><div><span>Records reviewed</span><strong>{data.detail.ehr_history.length + data.detail.iot_observations.length}</strong><small>synthetic observations</small></div></div>
    <section className="evidence-section" aria-labelledby="ehr-heading"><h2 id="ehr-heading">Synthetic EHR history</h2><p>Longitudinal clinical records. Creatinine and eGFR are shown independently because their units and direction differ.</p><div className="dual-chart"><div><h3>Creatinine trend</h3><div className="chart-frame" aria-label="Creatinine history chart"><ResponsiveContainer width="100%" height={230}><LineChart data={creatinine}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" tick={false} /><YAxis unit=" mg/dL" width={78} /><Tooltip /><Line type="monotone" dataKey="value" name="Creatinine" stroke="#0d665d" strokeWidth={3} dot={{ r: 2 }} /></LineChart></ResponsiveContainer></div></div><div><h3>eGFR trend</h3><div className="chart-frame" aria-label="eGFR history chart"><ResponsiveContainer width="100%" height={230}><LineChart data={egfr}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" tick={false} /><YAxis width={48} /><Tooltip /><Line type="monotone" dataKey="value" name="eGFR" stroke="#376e9a" strokeWidth={3} dot={{ r: 2 }} /></LineChart></ResponsiveContainer></div></div></div><ul className="record-list">{data.detail.ehr_history.slice().reverse().map((event) => <li key={event.event_id}><strong>{event.event_type}</strong><span>{formatTime(event.event_time)}</span><span>{String(event.data.test_name ?? event.data.medication ?? event.data.encounter_type ?? "Synthetic record")} {event.data.value !== undefined ? `: ${event.data.value} ${event.data.unit ?? ""}` : ""}</span></li>)}</ul></section>
    <section className="evidence-section" aria-labelledby="iot-heading"><h2 id="iot-heading">Simulated medical-IoT trends</h2><p>Wearable and home-monitoring observations, maintained as a separate time-series stream.</p><div className="chart-frame" aria-label="Systolic blood pressure trend chart"><ResponsiveContainer width="100%" height={240}><LineChart data={bloodPressure}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" hide /><YAxis unit=" mmHg" /><Tooltip /><Line type="monotone" dataKey="value" stroke="#376e9a" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></section>
    <div className="clinical-grid">
      <section className="evidence-section rule-detail" aria-labelledby="rule-heading"><p className="context-label">Observed state</p><h2 id="rule-heading">Current clinical rule</h2><strong>{data.rule ? ruleLabels[data.rule.status] : "Insufficient creatinine history"}</strong><p>{data.rule?.limitation ?? "No stored rule evidence is available."}</p></section>
      <section className="evidence-section prediction-detail" aria-labelledby="prediction-heading"><p className="context-label">Future model output</p><h2 id="prediction-heading">24-hour AKI prediction</h2><strong>{data.prediction?.status === "available" ? `${Math.round(data.prediction.probability * 100)}%` : "Risk unavailable"}</strong><p>Prediction generated: {data.prediction?.generated_at ? formatTime(data.prediction.generated_at) : "Not available"}</p>{warning && <p className="quality-warning"><span className="data-label">Data quality warning</span>{warning}</p>}</section>
    </div>
    <section className="evidence-section" aria-labelledby="shap-heading"><p className="context-label">Explanation / not causal</p><h2 id="shap-heading">SHAP feature influence</h2>{attributions.length ? <ol className="shap-list">{attributions.map((item) => <li key={item.feature}><div><strong>{featureLabels[item.feature] ?? item.feature}</strong><span>Input value: {item.value.toLocaleString()}</span></div><div className="shap-measure"><span className={item.shap_margin >= 0 ? "shap-bar shap-bar--higher" : "shap-bar shap-bar--lower"} style={{ width: `${maxInfluence ? Math.max(3, Math.abs(item.shap_margin) / maxInfluence * 100) : 3}%` }} /><strong>{item.shap_margin >= 0 ? "+" : ""}{item.shap_margin.toFixed(5)}</strong></div></li>)}</ol> : <p>Explanation unavailable because there is no valid prediction.</p>} {maxInfluence > 0 && maxInfluence < 0.0005 && <p className="quality-clear">All measured feature influences are very small for this model output. They are shown with five-decimal precision rather than rounded to zero.</p>}<p>Positive values push this model output toward higher predicted risk; negative values push it lower. SHAP does not establish causation or treatment guidance.</p></section>
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
