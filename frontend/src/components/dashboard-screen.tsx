"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DoctorDashboard } from "@/components/doctor-dashboard";
import { ClinicianSidebar } from "@/components/clinician-sidebar";
import { ApiError, fetchDoctorDashboard, fetchDoctorHealth, type DashboardPatient } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

type DashboardState = "loading" | "ready" | "error" | "unauthorized" | "unavailable";

type DashboardView = "overview" | "patients";

export function DashboardScreen({ view }: { view: DashboardView }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<DashboardPatient[]>([]);
  const [state, setState] = useState<DashboardState>("loading");
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async (activeUser: User, refresh = false) => {
    if (refresh) {
      setRefreshing(true);
    }
    else setState("loading");
    try {
      const token = await activeUser.getIdToken();
      await fetchDoctorHealth(token);
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
    } finally {
      setRefreshing(false);
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
          <h1 id="dashboard-title">{view === "overview" ? "Clinical overview" : "Monitored patients"}</h1>
          <p>{view === "overview" ? "A clear starting point for reviewing the simulated CKD cohort." : "Review current clinical evidence and future 24-hour AKI risk as separate signals."}</p>
        </div>
        <div className="dashboard-sync">
          <span>Research prototype</span><strong>Synthetic data only</strong>
        </div>
      </section>

      {view === "overview" && <section className="overview-page" aria-label="Cohort overview">
        <div className="overview-metrics"><div><strong>{rows.length}</strong><span>Monitored patients</span></div><div><strong>{criteriaMet}</strong><span>Need current-rule review</span></div><div><strong>{unavailablePredictions}</strong><span>Risk results unavailable</span></div></div>
        <div className="overview-columns"><section className="priority-panel"><div><h2>Review priority</h2><p>Patients meeting current creatinine criteria. This is observed evidence, not predicted risk.</p></div>{priorityPatients.length ? <ul>{priorityPatients.map((row) => <li key={row.patient.patient_id}><div><strong>{row.patient.display_name}</strong><span>Age {row.patient.age} · CKD {row.patient.ckd_stage}</span></div><Link href={`/patients/${row.patient.patient_id}`}>Open record</Link></li>)}</ul> : <p>No current criteria are met.</p>}<Link className="primary-button" href="/patients">View all monitored patients</Link></section><section className="overview-guide"><h2>Evidence status</h2><dl><div><dt>Current clinical rules</dt><dd>{criteriaMet} require review</dd></div><div><dt>24-hour predictions</dt><dd>{predictionsAvailable} valid, {unavailablePredictions} unavailable</dd></div><div><dt>Data source</dt><dd>Synthetic EHR + simulated IoT</dd></div></dl></section></div>
      </section>}

      {view === "patients" && <><div className="page-tools"><button className="secondary-button" disabled={refreshing || !user} onClick={() => user && void loadDashboard(user, true)} type="button">{refreshing ? "Refreshing…" : "Refresh from Firestore"}</button></div><div id="monitored-patients"><DoctorDashboard
        rows={rows}
        loading={state === "loading"}
        error={state === "error" ? "general" : state === "unauthorized" ? "unauthorized" : state === "unavailable" ? "unavailable" : undefined}
        onRetry={user ? () => void loadDashboard(user) : undefined}
      /></div></>}
      </div>
    </main>
  );
}
