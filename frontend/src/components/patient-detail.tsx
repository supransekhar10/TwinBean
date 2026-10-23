"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ApiError, createReviewNote, fetchPatientTwin, fetchReviewNotes, type AkiPrediction, type ClinicalRuleResult, type PatientDetail, type ReviewNote } from "../lib/api";
import { firebaseAuth } from "../lib/firebase";
import { ClinicianSidebar } from "./clinician-sidebar";
import { DownloadReportButton } from "./download-report-button";

type TwinData = { detail: PatientDetail; rule: ClinicalRuleResult | null; prediction: AkiPrediction | null };
const featureLabels: Record<string, string> = { age_years: "Age", latest_creatinine_mg_dl: "Latest creatinine", creatinine_delta_48h_mg_dl: "48-hour creatinine change", latest_systolic_bp_mmhg: "Latest systolic blood pressure" };
const ruleLabels = { criteria_met: "Criteria met", criteria_not_met: "Criteria not met", insufficient_creatinine_history: "Insufficient creatinine history" };

function formatTime(value: string) { return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC"; }
export function PatientDetailView({ data }: { data: TwinData }) {
  const creatinine = data.detail.ehr_history.filter((event) => event.event_type === "laboratory" && event.data.test_name === "creatinine").map((event) => ({ time: formatTime(event.event_time), value: Number(event.data.value) }));
  const egfr = data.detail.ehr_history.filter((event) => event.event_type === "laboratory" && event.data.test_name === "egfr").map((event) => ({ time: formatTime(event.event_time), value: Number(event.data.value) }));
  const bloodPressure = data.detail.iot_observations.filter((item) => item.measurement_type === "blood_pressure").map((item) => ({ time: formatTime(item.observed_at), value: Number(item.data.systolic) }));
  const attributions = data.prediction?.status === "available" ? [...data.prediction.attributions].sort((a, b) => Math.abs(b.shap_margin) - Math.abs(a.shap_margin)) : [];
  const maxInfluence = Math.max(...attributions.map((item) => Math.abs(item.shap_margin)), 0);
  const expectedMargin = attributions[0]?.expected_value;
  const explainedMargin = expectedMargin === undefined ? undefined : expectedMargin + attributions.reduce((sum, item) => sum + item.shap_margin, 0);
  const reconstructedRisk = explainedMargin === undefined ? undefined : 100 / (1 + Math.exp(-explainedMargin));
  const latestCreatinine = creatinine.at(-1)?.value;
  const latestSystolic = bloodPressure.at(-1)?.value;
  const modelInputs = [
    ["Age", `${data.detail.patient.age} years`],
    ["Latest creatinine", latestCreatinine === undefined ? "Unavailable" : `${latestCreatinine.toFixed(2)} mg/dL`],
    ["48-hour creatinine change", creatinine.length > 1 ? `${(creatinine.at(-1)!.value - creatinine.at(-2)!.value).toFixed(2)} mg/dL` : "Unavailable"],
    ["Latest systolic blood pressure", latestSystolic === undefined ? "Unavailable" : `${latestSystolic.toFixed(0)} mmHg`],
  ];
  return <div className="detail-shell">
    <header className="detail-header"><div><p className="context-label">Synthetic patient digital twin</p><h1>{data.detail.patient.display_name}</h1><p>Age {data.detail.patient.age}{data.detail.patient.sex ? ` / ${data.detail.patient.sex}` : ""} / CKD stage {data.detail.patient.ckd_stage}</p>{data.detail.patient.ckd_context && <p>{data.detail.patient.ckd_context}</p>}</div><div className="detail-actions"><DownloadReportButton patientId={data.detail.patient.patient_id} patientName={data.detail.patient.display_name} /><Link className="secondary-button" href="/patients">Back to monitored patients</Link></div></header>
    <p className="prototype-notice">Research prototype / synthetic data only / not for clinical use</p>
    <div className="metric-grid"><div><span>Latest creatinine</span><strong>{creatinine.at(-1)?.value.toFixed(2) ?? "Unavailable"}</strong><small>mg/dL</small></div><div><span>Latest eGFR</span><strong>{egfr.at(-1)?.value.toFixed(1) ?? "Unavailable"}</strong><small>mL/min/1.73m²</small></div><div><span>Latest systolic BP</span><strong>{bloodPressure.at(-1)?.value.toFixed(0) ?? "Unavailable"}</strong><small>mmHg</small></div><div><span>Available data points</span><strong>{data.detail.ehr_history.length + data.detail.iot_observations.length}</strong><small>synthetic observations</small></div></div>
    <section className="evidence-section" aria-labelledby="ehr-heading"><h2 id="ehr-heading">Synthetic EHR history</h2><p>Creatinine and eGFR trends remain separate because their units and clinical direction differ.</p><div className="dual-chart"><div><h3>Creatinine trend</h3><div className="chart-frame" aria-label="Creatinine history chart"><ResponsiveContainer width="100%" height={230}><LineChart data={creatinine}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" tick={false} /><YAxis unit=" mg/dL" width={78} /><Tooltip /><Line type="monotone" dataKey="value" name="Creatinine" stroke="#0d665d" strokeWidth={3} dot={{ r: 2 }} /></LineChart></ResponsiveContainer></div></div><div><h3>eGFR trend</h3><div className="chart-frame" aria-label="eGFR history chart"><ResponsiveContainer width="100%" height={230}><LineChart data={egfr}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" tick={false} /><YAxis width={48} /><Tooltip /><Line type="monotone" dataKey="value" name="eGFR" stroke="#376e9a" strokeWidth={3} dot={{ r: 2 }} /></LineChart></ResponsiveContainer></div></div></div><div className="recent-records-heading"><h3>Latest records</h3><span>Showing 8 of {data.detail.ehr_history.length}</span></div><ul className="record-list">{data.detail.ehr_history.slice().reverse().slice(0, 8).map((event) => <li key={event.event_id}><strong>{String(event.data.test_name ?? event.data.medication ?? event.data.encounter_type ?? event.event_type)}</strong><span>{event.data.value !== undefined ? `${event.data.value} ${event.data.unit ?? ""}` : "Recorded"}</span><time>{formatTime(event.event_time)}</time></li>)}</ul></section>
    <section className="evidence-section" aria-labelledby="iot-heading"><h2 id="iot-heading">Simulated medical-IoT trends</h2><p>Wearable and home-monitoring observations, maintained as a separate time-series stream.</p><div className="chart-frame" aria-label="Systolic blood pressure trend chart"><ResponsiveContainer width="100%" height={240}><LineChart data={bloodPressure}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" hide /><YAxis unit=" mmHg" /><Tooltip /><Line type="monotone" dataKey="value" stroke="#376e9a" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></section>
    <div className="clinical-grid">
      <section className="evidence-section rule-detail" aria-labelledby="rule-heading"><p className="context-label">Observed state</p><h2 id="rule-heading">Current clinical rule</h2><strong>{data.rule ? ruleLabels[data.rule.status] : "Insufficient creatinine history"}</strong><p>{data.rule?.limitation ?? "No stored rule evidence is available."}</p></section>
      <section className="evidence-section prediction-detail" aria-labelledby="prediction-heading"><p className="context-label">Future model output</p><h2 id="prediction-heading">24-hour AKI prediction</h2><strong>{data.prediction?.status === "available" ? `${(data.prediction.probability * 100).toFixed(1)}%` : "Risk unavailable"}</strong><p>Prediction generated: {data.prediction?.generated_at ? formatTime(data.prediction.generated_at) : "Not available"}</p></section>
    </div>
    <section className="evidence-section" aria-labelledby="shap-heading"><p className="context-label">Explanation / not causal</p><h2 id="shap-heading">SHAP feature influence</h2>{attributions.length ? <><div className="risk-formula"><strong>How this probability is calculated</strong><code>risk = 100 × sigmoid(base margin + Σ SHAP contributions)</code><span>Reconstructed model output: {reconstructedRisk?.toFixed(3)}%</span></div><ol className="shap-list">{attributions.map((item) => <li key={item.feature}><div><strong>{featureLabels[item.feature] ?? item.feature}</strong><span>Input value: {item.value.toLocaleString()}</span></div><div className="shap-measure"><span className={item.shap_margin >= 0 ? "shap-bar shap-bar--higher" : "shap-bar shap-bar--lower"} style={{ width: `${maxInfluence ? Math.max(3, Math.abs(item.shap_margin) / maxInfluence * 100) : 3}%` }} /><strong>{item.shap_margin >= 0 ? "+" : ""}{item.shap_margin.toFixed(5)}</strong></div></li>)}</ol></> : <div className="shap-unavailable"><div><strong>No SHAP explanation available</strong><p>A valid model prediction is required before feature influence can be calculated. No zero values are substituted.</p></div><dl>{modelInputs.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><small>Model inputs shown for readiness only; these are not SHAP values or causal effects.</small></div>} {maxInfluence > 0 && maxInfluence < 0.0005 && <p className="quality-clear">All measured feature influences are very small for this model output. They are shown with five-decimal precision rather than rounded to zero.</p>}{attributions.length > 0 && <p>Positive values push this model output toward higher predicted risk; negative values push it lower. SHAP does not establish causation or treatment guidance.</p>}</section>
  </div>;
}

export function PatientDetailScreen({ patientId }: { patientId: string }) {
  const [state, setState] = useState<"loading" | "ready" | "error" | "unauthorized">("loading");
  const [data, setData] = useState<TwinData | null>(null);
  const [notes, setNotes] = useState<ReviewNote[]>([]);
  const [noteState, setNoteState] = useState<"idle" | "saving" | "error">("idle");
  const [user, setUser] = useState<User | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadPatient = useCallback(async (activeUser: User, initial = false) => {
    if (initial) setState("loading");
    try {
      const token = await activeUser.getIdToken();
      const [patientData, reviewNotes] = await Promise.all([
        fetchPatientTwin(patientId, token),
        fetchReviewNotes(patientId, token),
      ]);
      setData(patientData);
      setNotes(reviewNotes);
      setState("ready");
    }
    catch (error) {
      if (initial) setState(error instanceof ApiError && (error.status === 401 || error.status === 403) ? "unauthorized" : "error");
    }
  }, [patientId]);

  useEffect(() => onAuthStateChanged(firebaseAuth, (activeUser) => {
    if (!activeUser) { setState("unauthorized"); return; }
    setUser(activeUser);
    void loadPatient(activeUser, true);
  }), [loadPatient]);

  const refreshPatient = useCallback(async () => {
    if (!user || refreshing) return;
    setRefreshing(true);
    try { await loadPatient(user); }
    finally { setRefreshing(false); }
  }, [loadPatient, refreshing, user]);

  if (state === "loading") {
    return null;
  }

  const content = state === "unauthorized"
      ? <div className="detail-shell detail-state"><h1>Doctor access is required</h1><p>Sign in with an approved doctor account.</p><Link className="primary-button" href="/">Return to sign in</Link></div>
      : state === "error" || !data
        ? <div className="detail-shell detail-state"><h1>Patient detail could not be loaded</h1><p>Check the backend connection and return to the patient list to retry.</p><Link className="secondary-button" href="/patients">Back to monitored patients</Link></div>
        : <><PatientDetailView data={data} /><section className="evidence-section review-notes" id="review-notes"><h2>Doctor review notes</h2><p>Document observations about this synthetic case. Notes remain separate from clinical rules, predictions, and SHAP explanations.</p><form onSubmit={async (event) => { event.preventDefault(); const form = event.currentTarget; const input = new FormData(form).get("note"); if (typeof input !== "string" || !input.trim() || !firebaseAuth.currentUser) return; setNoteState("saving"); try { const saved = await createReviewNote(patientId, input.trim(), await firebaseAuth.currentUser.getIdToken()); setNotes((current) => [saved, ...current]); form.reset(); setNoteState("idle"); } catch { setNoteState("error"); } }}><label><span>Review note</span><textarea name="note" required maxLength={2000} rows={4} placeholder="Record a clinical observation about this synthetic patient…" /></label><div><button className="primary-button" disabled={noteState === "saving"} type="submit">{noteState === "saving" ? "Saving…" : "Save review note"}</button>{noteState === "error" && <span role="alert">Note could not be saved. Check Firestore and retry.</span>}</div></form>{notes.length ? <ol>{notes.map((note) => <li key={note.note_id}><p>{note.text}</p><small>{formatTime(note.created_at)} · Doctor review</small></li>)}</ol> : <p>No doctor review notes yet.</p>}</section></>;
  return <main className="dashboard-shell"><ClinicianSidebar active="patients" email={user?.email} onRefresh={refreshPatient} refreshing={refreshing} /><div className="dashboard-content">{content}</div></main>;
}
