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

  return (
    <main className="dashboard-shell">
      <header className="dashboard-bar">
        <div className="wordmark" aria-label="TwinBean doctor dashboard">
          <span className="wordmark-mark" aria-hidden="true">TB</span>
          <span>TwinBean</span>
        </div>
        <div className="account-menu">
          <span title={user?.email ?? undefined}>{user?.email ?? "Doctor account"}</span>
          <button className="text-button" onClick={handleSignOut} type="button">Sign out</button>
        </div>
      </header>

      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <p className="context-label">Doctor dashboard</p>
          <h1 id="dashboard-title">Monitored patients</h1>
          <p>Review current clinical evidence and future 24-hour AKI risk as separate signals.</p>
        </div>
        <div className="dashboard-sync">
          <button className="secondary-button" disabled={refreshing || !user} onClick={() => user && void loadDashboard(user, true)} type="button">
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </section>

      <DoctorDashboard
        rows={rows}
        loading={state === "loading"}
        error={state === "error" ? "general" : state === "unauthorized" ? "unauthorized" : state === "unavailable" ? "unavailable" : undefined}
        onRetry={user ? () => void loadDashboard(user) : undefined}
      />
    </main>
  );
}
