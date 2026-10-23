"use client";

import { signOut } from "@firebase/auth";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { firebaseAuth } from "../lib/firebase";

type ActivePage = "overview" | "patients" | "reviews" | "reports" | "assistant";

export function ClinicianSidebar({ active, email, onRefresh, refreshing = false }: { active: ActivePage; email?: string | null; onRefresh?: () => void | Promise<void>; refreshing?: boolean }) {
  const router = useRouter();
  async function handleSignOut() {
    await signOut(firebaseAuth);
    router.replace("/");
  }
  return <aside className="clinician-sidebar" aria-label="Doctor workspace navigation">
    <Link className="sidebar-brand" href="/dashboard" aria-label="TwinBean overview">
      <Image src="/twinbean-logo.png" alt="" width={48} height={48} priority />
      <div><strong>TwinBean</strong><span>Kidney digital twin</span></div>
    </Link>
    <nav className="sidebar-nav">
      <Link className={`sidebar-link sidebar-link--overview${active === "overview" ? " sidebar-link--active" : ""}`} href="/dashboard">Overview</Link>
      <Link className={`sidebar-link sidebar-link--patients${active === "patients" ? " sidebar-link--active" : ""}`} href="/patients">Monitored patients</Link>
      <Link className={`sidebar-link sidebar-link--reviews${active === "reviews" ? " sidebar-link--active" : ""}`} href="/reviews">Review workspace</Link>
      <Link className={`sidebar-link sidebar-link--reports${active === "reports" ? " sidebar-link--active" : ""}`} href="/reports">Patient reports</Link>
      <Link className={`sidebar-link sidebar-link--assistant${active === "assistant" ? " sidebar-link--active" : ""}`} href="/assistant">Twini assistant</Link>
      <button aria-busy={refreshing} className="sidebar-link sidebar-link--refresh" disabled={refreshing || !onRefresh} onClick={() => void onRefresh?.()} type="button">{refreshing ? "Refreshing…" : "Refresh Data"}</button>
    </nav>
    <div className="sidebar-account"><span>Signed in as</span><strong title={email ?? undefined}>{email ?? "Doctor account"}</strong><button className="sidebar-signout" onClick={handleSignOut} type="button">Sign out</button></div>
  </aside>;
}
