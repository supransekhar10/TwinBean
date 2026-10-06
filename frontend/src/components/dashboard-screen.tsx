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

type DashboardView = "overview" | "patients" | "add";
const draftKey = "twinbean-session-patients";

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
      const storedRows = refresh ? [] : JSON.parse(sessionStorage.getItem(draftKey) ?? "[]") as DashboardPatient[];
      if (refresh) sessionStorage.removeItem(draftKey);
      setRows([...storedRows, ...await fetchDoctorDashboard(token, refresh)]);
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

  function handleAddPatient(formData: FormData) {
    const displayName = String(formData.get("displayName") ?? "").trim();
    const age = Number(formData.get("age"));
    const sex = String(formData.get("sex") ?? "");
    const ckdStage = String(formData.get("ckdStage") ?? "G3a");
    if (!displayName || !Number.isInteger(age) || age < 18 || age > 100) return;
    const suffix = crypto.randomUUID().replaceAll("-", "");
    const draft: DashboardPatient = {
      patient: {
        patient_id: `tbp-${suffix}`,
        display_name: displayName,
        age,
        sex,
        ckd_stage: ckdStage,
        ckd_context: `Adult with chronic kidney disease stage ${ckdStage}; session-only synthetic record.`,
      },
      current_rule: null,
      prediction: { status: "unavailable", reasons: ["no_stored_prediction"], warnings: [] },
      sessionDraft: true,
    };
    const existing = JSON.parse(sessionStorage.getItem(draftKey) ?? "[]") as DashboardPatient[];
    sessionStorage.setItem(draftKey, JSON.stringify([draft, ...existing]));
    router.push("/patients");
  }

  const criteriaMet = rows.filter((row) => row.current_rule?.status === "criteria_met").length;
  const predictionsAvailable = rows.filter((row) => row.prediction.status === "available").length;

  return (
    <main className="dashboard-shell">
      <ClinicianSidebar active={view} email={user?.email} />

      <div className="dashboard-content" id="patient-dashboard">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">{view === "overview" ? "Clinical overview" : view === "add" ? "Add synthetic patient" : "Monitored patients"}</h1>
          <p>{view === "overview" ? "A clear starting point for reviewing the simulated CKD cohort." : view === "add" ? "Create a fictional session record without changing the authoritative Firestore cohort." : "Review current clinical evidence and future 24-hour AKI risk as separate signals."}</p>
        </div>
        <div className="dashboard-sync">
          <span>Research prototype</span><strong>Synthetic data only</strong>
        </div>
      </section>

      {view === "overview" && <section className="overview-page" aria-label="Cohort overview">
        <div className="overview-metrics"><div><strong>{rows.length}</strong><span>Monitored synthetic patients</span></div><div><strong>{criteriaMet}</strong><span>Current criteria met</span></div><div><strong>{predictionsAvailable}</strong><span>Valid predictions available</span></div></div>
        <div className="overview-actions"><div><h2>Review the cohort</h2><p>Open the prioritized patient list to review current rules and future risk separately.</p><Link className="primary-button" href="/patients">Open monitored patients</Link></div><div><h2>Add a demonstration record</h2><p>Create a clearly labelled session-only synthetic patient for interface testing.</p><Link className="secondary-button" href="/patients/new">Add synthetic patient</Link></div></div>
      </section>}

      {view === "add" && <section className="add-patient-panel add-patient-page" aria-labelledby="add-patient-title">
        <div><h2 id="add-patient-title">Add a synthetic patient</h2><p>This creates a session-only demonstration record. Refreshing restores the authoritative Firestore cohort.</p></div>
        <form action={handleAddPatient}>
          <label><span>Fictional patient name</span><input name="displayName" required maxLength={60} placeholder="e.g. Kavya Rao" /></label>
          <label><span>Age</span><input name="age" required type="number" min="18" max="100" /></label>
          <label><span>Sex</span><select name="sex" defaultValue="female"><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select></label>
          <label><span>CKD stage</span><select name="ckdStage" defaultValue="G3b"><option>G3a</option><option>G3b</option><option>G4</option></select></label>
          <div className="add-patient-actions"><button className="primary-button" type="submit">Add to this session</button><Link className="text-button" href="/patients">Cancel</Link></div>
        </form>
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
