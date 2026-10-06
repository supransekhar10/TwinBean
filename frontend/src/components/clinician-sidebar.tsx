"use client";

import { signOut } from "@firebase/auth";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { firebaseAuth } from "../lib/firebase";

type ActivePage = "overview" | "patients" | "reviews";

export function ClinicianSidebar({ active, email }: { active: ActivePage; email?: string | null }) {
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
      <Link className={`sidebar-link${active === "overview" ? " sidebar-link--active" : ""}`} href="/dashboard">Overview</Link>
      <Link className={`sidebar-link${active === "patients" ? " sidebar-link--active" : ""}`} href="/patients">Monitored patients</Link>
      <Link className={`sidebar-link${active === "reviews" ? " sidebar-link--active" : ""}`} href="/reviews">Review workspace</Link>
    </nav>
    <div className="sidebar-account"><span>Signed in as</span><strong title={email ?? undefined}>{email ?? "Doctor account"}</strong><button className="sidebar-signout" onClick={handleSignOut} type="button">Sign out</button></div>
  </aside>;
}
