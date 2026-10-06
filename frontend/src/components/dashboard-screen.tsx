"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { DoctorDashboard } from "@/components/doctor-dashboard";
import { ClinicianSidebar } from "@/components/clinician-sidebar";
import { ApiError, fetchDoctorDashboard, type DashboardPatient } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

type DashboardState = "loading" | "ready" | "error" | "unauthorized" | "unavailable";

type DashboardView = "overview" | "patients" | "reviews";

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

  const loadDashboard = useCallback(async (activeUser: User, refresh = false) => {
    if (!refresh) setState("loading");
    try {
      const token = await activeUser.getIdToken();
      setRows(await fetchDoctorDashboard(token, refresh));
      setState("ready");
    } catch (error) {
      if (refresh) {
        setState("ready");
        return;
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
    const forceRefresh = sessionStorage.getItem("twinbean-force-refresh") === "1";
    sessionStorage.removeItem("twinbean-force-refresh");
    void loadDashboard(activeUser, forceRefresh);
  }), [loadDashboard, router]);

  const criteriaMet = rows.filter((row) => row.current_rule?.status === "criteria_met").length;
  const predictionsAvailable = rows.filter((row) => row.prediction.status === "available").length;
  const unavailablePredictions = rows.length - predictionsAvailable;
  const priorityPatients = rows.filter((row) => row.current_rule?.status === "criteria_met").slice(0, 4);

  return (
    <main className="dashboard-shell">
      <ClinicianSidebar active={view} email={user?.email} />

      <div className="dashboard-content" id="patient-dashboard">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">{view === "overview" ? "Clinical overview" : view === "reviews" ? "Review workspace" : "Monitored patients"}</h1>
          <p>{view === "overview" ? "A clear starting point for reviewing the simulated CKD cohort." : view === "reviews" ? "Open priority patients and record doctor observations separately from generated evidence." : "Review current clinical evidence and future 24-hour AKI risk as separate signals."}</p>
        </div>
        <div className="dashboard-sync">
          <span>Research prototype</span><strong>Synthetic data only</strong>
        </div>
      </section>

      {view === "overview" && <section className="overview-page" aria-label="Cohort overview">
        <div className="overview-metrics"><div><CountUp value={rows.length} /><span>Monitored patients</span></div><div><CountUp value={criteriaMet} /><span>Need current-rule review</span></div><div><CountUp value={unavailablePredictions} /><span>Risk results unavailable</span></div></div>
        <div className="overview-columns"><section className="priority-panel"><div><h2>Review priority</h2><p>Patients meeting current creatinine criteria. This is observed evidence, not predicted risk.</p></div>{priorityPatients.length ? <ul>{priorityPatients.map((row) => <li key={row.patient.patient_id}><div><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage}</span></div><Link href={`/patients/${row.patient.patient_id}`}>Open record</Link></li>)}</ul> : <p>No current criteria are met.</p>}<Link className="primary-button" href="/patients">View all monitored patients</Link></section><section className="overview-guide"><h2>Evidence status</h2><dl><div><dt>Current clinical rules</dt><dd>{criteriaMet} require review</dd></div><div><dt>24-hour predictions</dt><dd>{predictionsAvailable} valid, {unavailablePredictions} unavailable</dd></div><div><dt>Data source</dt><dd>Synthetic EHR + simulated IoT</dd></div></dl></section></div>
      </section>}

      {view === "reviews" && <section className="review-workspace"><div><h2>Patients awaiting review</h2><p>Open a record to add a doctor review note. Notes do not change clinical-rule or prediction outputs.</p></div><ul>{priorityPatients.map((row) => <li key={row.patient.patient_id}><div><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage} · Current criteria met</span></div><Link className="primary-button" href={`/patients/${row.patient.patient_id}#review-notes`}>Review patient</Link></li>)}</ul></section>}

      {view === "patients" && <div id="monitored-patients"><DoctorDashboard
        rows={rows}
        loading={state === "loading"}
        error={state === "error" ? "general" : state === "unauthorized" ? "unauthorized" : state === "unavailable" ? "unavailable" : undefined}
        onRetry={user ? () => void loadDashboard(user) : undefined}
      /></div>}
      </div>
    </main>
  );
}
