"use client";

import { onAuthStateChanged, signOut, type User } from "@firebase/auth";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DoctorDashboard } from "@/components/doctor-dashboard";
import { ApiError, fetchDoctorDashboard, fetchDoctorHealth, type DashboardPatient } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

type DashboardState = "loading" | "ready" | "error" | "unauthorized" | "unavailable";

export function DashboardScreen() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<DashboardPatient[]>([]);
  const [state, setState] = useState<DashboardState>("loading");
  const [refreshing, setRefreshing] = useState(false);
  const [showAddPatient, setShowAddPatient] = useState(false);

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

  async function handleSignOut() {
    await signOut(firebaseAuth);
    router.replace("/");
  }

  function handleAddPatient(formData: FormData) {
    const displayName = String(formData.get("displayName") ?? "").trim();
    const age = Number(formData.get("age"));
    const sex = String(formData.get("sex") ?? "");
    const ckdStage = String(formData.get("ckdStage") ?? "G3a");
    if (!displayName || !Number.isInteger(age) || age < 18 || age > 100) return;
    const suffix = crypto.randomUUID().replaceAll("-", "");
    setRows((current) => [{
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
    }, ...current]);
    setShowAddPatient(false);
  }

  return (
    <main className="dashboard-shell">
      <aside className="clinician-sidebar" aria-label="Doctor workspace navigation">
        <div className="sidebar-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/twinbean-logo.png" alt="" />
          <div><strong>TwinBean</strong><span>Kidney digital twin</span></div>
        </div>
        <nav className="sidebar-nav">
          <a className="sidebar-link sidebar-link--active" href="#patient-dashboard">Overview</a>
          <a className="sidebar-link" href="#monitored-patients">Monitored patients</a>
          <button className="sidebar-link" onClick={() => setShowAddPatient((value) => !value)} type="button">Add synthetic patient</button>
          <button className="sidebar-link" disabled={refreshing || !user} onClick={() => user && void loadDashboard(user, true)} type="button">{refreshing ? "Refreshing…" : "Refresh cohort"}</button>
        </nav>
        <div className="sidebar-account">
          <span>Signed in as</span><strong title={user?.email ?? undefined}>{user?.email ?? "Doctor account"}</strong>
          <button className="sidebar-signout" onClick={handleSignOut} type="button">Sign out</button>
        </div>
      </aside>

      <div className="dashboard-content" id="patient-dashboard">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">Monitored patients</h1>
          <p>Review current clinical evidence and future 24-hour AKI risk as separate signals.</p>
        </div>
        <div className="dashboard-sync">
          <span>Research prototype</span><strong>Synthetic data only</strong>
        </div>
      </section>

      {showAddPatient && <section className="add-patient-panel" aria-labelledby="add-patient-title">
        <div><h2 id="add-patient-title">Add a synthetic patient</h2><p>This creates a session-only demonstration record. Refreshing restores the authoritative Firestore cohort.</p></div>
        <form action={handleAddPatient}>
          <label><span>Fictional patient name</span><input name="displayName" required maxLength={60} placeholder="e.g. Kavya Rao" /></label>
          <label><span>Age</span><input name="age" required type="number" min="18" max="100" /></label>
          <label><span>Sex</span><select name="sex" defaultValue="female"><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select></label>
          <label><span>CKD stage</span><select name="ckdStage" defaultValue="G3b"><option>G3a</option><option>G3b</option><option>G4</option></select></label>
          <div className="add-patient-actions"><button className="primary-button" type="submit">Add to this session</button><button className="text-button" onClick={() => setShowAddPatient(false)} type="button">Cancel</button></div>
        </form>
      </section>}

      <div id="monitored-patients"><DoctorDashboard
        rows={rows}
        loading={state === "loading"}
        error={state === "error" ? "general" : state === "unauthorized" ? "unauthorized" : state === "unavailable" ? "unavailable" : undefined}
        onRetry={user ? () => void loadDashboard(user) : undefined}
      /></div>
      </div>
    </main>
  );
}
