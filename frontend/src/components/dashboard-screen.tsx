"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { DoctorDashboard } from "@/components/doctor-dashboard";
import { ClinicianSidebar } from "@/components/clinician-sidebar";
import { DownloadReportButton } from "@/components/download-report-button";
import { ApiError, fetchDoctorDashboard, type DashboardPatient } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

type DashboardState = "loading" | "ready" | "error" | "unauthorized" | "unavailable";

type DashboardView = "overview" | "patients" | "reviews" | "reports";

function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(value ? 1 : 0);
  const frame = useRef<number | null>(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || value <= 1) { frame.current = requestAnimationFrame(() => setDisplay(value)); return () => { if (frame.current !== null) cancelAnimationFrame(frame.current); }; }
    const started = performance.now();
    const update = (now: number) => { const progress = Math.min(1, (now - started) / 280); setDisplay(Math.max(1, Math.round(value * progress))); if (progress < 1) frame.current = requestAnimationFrame(update); };
    frame.current = requestAnimationFrame(update);
    return () => { if (frame.current !== null) cancelAnimationFrame(frame.current); };
  }, [value]);
  return <strong className="count-up">{display}</strong>;
}

export function DashboardScreen({ view }: { view: DashboardView }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<DashboardPatient[]>([]);
  const [state, setState] = useState<DashboardState>("loading");
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async (activeUser: User, refresh = false) => {
    if (!refresh) setState("loading");
    try {
      const token = await activeUser.getIdToken();
      setRows(await fetchDoctorDashboard(token, refresh));
      setState("ready");
    } catch (error) {
      if (refresh) {
        try {
          const token = await activeUser.getIdToken();
          setRows(await fetchDoctorDashboard(token));
          setState("ready");
          return;
        } catch (fallbackError) {
          error = fallbackError;
        }
      }
      setState(
        error instanceof ApiError && (error.status === 503 || error.status === 504)
          ? "unavailable"
          : error instanceof ApiError && (error.status === 401 || error.status === 403)
            ? "unauthorized"
            : error instanceof Error && error.message.includes("Doctor access is required")
              ? "unauthorized"
              : "error",
      );
    }
  }, []);

  useEffect(() => onAuthStateChanged(firebaseAuth, (activeUser) => {
    if (!activeUser) {
      router.replace("/");
      return;
    }
    setUser(activeUser);
    void loadDashboard(activeUser);
  }), [loadDashboard, router]);

  const refreshDashboard = useCallback(async () => {
    if (!user || refreshing) return;
    setRefreshing(true);
    try {
      await loadDashboard(user, true);
    } finally {
      setRefreshing(false);
    }
  }, [loadDashboard, refreshing, user]);

  if (state === "loading") {
    return null;
  }

  if (state !== "ready") {
    const unauthorized = state === "unauthorized";
    return <main className="dashboard-shell"><ClinicianSidebar active={view} email={user?.email} onRefresh={refreshDashboard} refreshing={refreshing} /><div className="dashboard-content"><section className="dashboard-state"><h1>{unauthorized ? "Doctor access is required" : "Patient evidence could not be loaded"}</h1><p>{unauthorized ? "Sign in with an approved doctor account." : "The last complete data snapshot is unavailable. Check the backend connection and retry."}</p><button className="primary-button" onClick={() => user && void loadDashboard(user)} type="button">Retry loading data</button></section></div></main>;
  }

  const rulesAssessed = rows.filter((row) => row.current_rule !== null).length;
  const criteriaMet = rows.filter((row) => row.current_rule?.status === "criteria_met").length;
  const predictionsAvailable = rows.filter((row) => row.prediction.status === "available").length;
  const rulePriorityPatients = rows.filter((row) => row.current_rule?.status === "criteria_met");
  const predictionPriorityPatients = [...rows]
    .filter((row) => row.prediction.status === "available")
    .sort((left, right) => {
      const leftRisk = left.prediction.status === "available" ? left.prediction.probability : -1;
      const rightRisk = right.prediction.status === "available" ? right.prediction.probability : -1;
      return rightRisk - leftRisk;
    });
  const priorityPatients = (rulePriorityPatients.length ? rulePriorityPatients : predictionPriorityPatients).slice(0, 4);
  const reviewPatients = (rulePriorityPatients.length ? rulePriorityPatients : predictionPriorityPatients)
    .filter((row) => !row.latest_review_at)
    .slice(0, 4);
  const priorityUsesPredictions = rulePriorityPatients.length === 0;

  return (
    <main className="dashboard-shell">
      <ClinicianSidebar active={view} email={user?.email} onRefresh={refreshDashboard} refreshing={refreshing} />

      <div className="dashboard-content" id="patient-dashboard">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">{view === "overview" ? "Clinical overview" : view === "reviews" ? "Review workspace" : view === "reports" ? "Patient reports" : "Monitored patients"}</h1>
          <p>{view === "overview" ? "A clear starting point for reviewing the simulated CKD cohort." : view === "reviews" ? "Open priority patients and record doctor observations separately from generated evidence." : view === "reports" ? "Generate a protected TwinBean PDF for one synthetic patient at a time." : "Review current clinical evidence and future 24-hour AKI risk as separate signals."}</p>
        </div>
        <div className="dashboard-sync">
          <span>Research prototype</span><strong>Synthetic data only</strong>
        </div>
      </section>

      {view === "overview" && <section className="overview-page" aria-label="Cohort overview">
        <div className="overview-metrics"><div><CountUp value={rows.length} /><span>Monitored patients</span></div><div><CountUp value={criteriaMet} /><span>Current criteria met</span></div><div><CountUp value={predictionsAvailable} /><span>Valid risk results</span></div></div>
        <div className="overview-columns"><section className="priority-panel"><header><div><h2>Review priority</h2><p>{priorityUsesPredictions ? "No current creatinine criteria are met. Showing the highest valid predicted 24-hour risk for review; this is model output, not a clinical rule." : "Patients meeting current creatinine criteria. This is observed evidence, not predicted risk."}</p></div><span className="priority-basis">{priorityUsesPredictions ? "Prediction priority" : "Clinical-rule priority"}</span></header>{priorityPatients.length ? <ol>{priorityPatients.map((row, index) => <li key={row.patient.patient_id}><span className="priority-rank" aria-hidden="true">{index + 1}</span><div><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage}</span></div><div className="priority-signal"><span>{priorityUsesPredictions ? "24-hour AKI risk" : "Current rule"}</span><strong>{priorityUsesPredictions && row.prediction.status === "available" ? `${(row.prediction.probability * 100).toFixed(1)}%` : "Criteria met"}</strong></div><Link href={`/patients/${row.patient.patient_id}`}>Open record</Link></li>)}</ol> : <p>No patients are currently available for prioritization.</p>}<Link className="primary-button" href="/patients">View all monitored patients</Link></section><section className="overview-guide"><h2>Evidence status</h2><dl><div><dt>Current clinical rules</dt><dd>{rulesAssessed} patients assessed</dd></div><div><dt>24-hour predictions</dt><dd>{predictionsAvailable} valid risk results</dd></div><div><dt>Priority review</dt><dd>{priorityPatients.length} patients highlighted</dd></div><div><dt>Data source</dt><dd>Synthetic EHR + simulated IoT</dd></div></dl></section></div>
      </section>}

      {view === "reviews" && <section className="review-workspace"><div><h2>Patients awaiting review</h2><p>Open a record to add a doctor review note. Once a note is saved, that patient leaves this pending queue.</p></div>{reviewPatients.length ? <ul>{reviewPatients.map((row) => <li key={row.patient.patient_id}><div className="review-patient"><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage}</span></div><div className="review-risk"><span>{priorityUsesPredictions ? "Predicted 24-hour risk" : "Current clinical rule"}</span><strong>{priorityUsesPredictions && row.prediction.status === "available" ? `${(row.prediction.probability * 100).toFixed(1)}%` : "Criteria met"}</strong></div><Link className="primary-button" href={`/patients/${row.patient.patient_id}#review-notes`}>Review patient</Link></li>)}</ul> : <div className="review-queue-empty"><strong>Review queue complete</strong><span>Every currently prioritized patient has a saved doctor note.</span><Link href="/patients">View monitored patients</Link></div>}</section>}

      {view === "reports" && <section className="reports-workspace" aria-labelledby="reports-heading"><div className="reports-heading"><div><h2 id="reports-heading">Individual synthetic patient reports</h2><p>Each PDF keeps observed rules, future risk, SHAP explanations, and doctor notes in clearly separated sections.</p></div><span>{rows.length} reports available</span></div><ul>{rows.map((row) => <li key={row.patient.patient_id}><div className="report-patient"><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage}</span></div><div className="report-status"><span>24-hour prediction</span><strong>{row.prediction.status === "available" ? `${(row.prediction.probability * 100).toFixed(1)}%` : "Risk unavailable"}</strong></div><Link className="report-open" href={`/patients/${row.patient.patient_id}`}>View record</Link><DownloadReportButton compact patientId={row.patient.patient_id} patientName={row.patient.display_name} /></li>)}</ul><p className="reports-disclaimer">Synthetic research data only. Downloaded reports are not clinical validation, diagnosis, or treatment guidance.</p></section>}

      {view === "patients" && <div id="monitored-patients"><DoctorDashboard
        rows={rows}
        onRetry={user ? () => void loadDashboard(user) : undefined}
      /></div>}
      </div>
    </main>
  );
}
