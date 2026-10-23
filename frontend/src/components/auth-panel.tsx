"use client";

import { onAuthStateChanged, signInWithEmailAndPassword, signOut } from "@firebase/auth";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { fetchDoctorHealth } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

function friendlyAuthError(error: unknown): string {
  if (error instanceof Error && error.message.includes("auth/invalid-credential")) {
    return "Email or password was not accepted. Check your details and try again.";
  }
  if (error instanceof Error && error.message.includes("Doctor access is required")) {
    return "This account is not approved for doctor access.";
  }
  if (error instanceof TypeError) {
    return "Signed in, but the protected backend could not be reached. Check that the TwinBean API is running.";
  }
  return "Sign-in could not be completed. Please try again.";
}

export function AuthPanel() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => onAuthStateChanged(firebaseAuth, async (user) => {
    if (!user) { setAuthChecked(true); return; }
    setWorking(true);
    try {
      await fetchDoctorHealth(await user.getIdToken());
      router.replace("/dashboard");
    } catch (error) {
      await signOut(firebaseAuth);
      setMessage(friendlyAuthError(error));
      setWorking(false);
      setAuthChecked(true);
    }
  }), [router]);

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setMessage("");
    let signedIn = false;
    try {
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      signedIn = true;
      const token = await credential.user.getIdToken(true);
      await fetchDoctorHealth(token);
      setPassword("");
      router.replace("/dashboard");
    } catch (error) {
      if (signedIn) await signOut(firebaseAuth);
      setMessage(friendlyAuthError(error));
      setWorking(false);
    }
  }

  return (
    <form aria-labelledby="sign-in-heading" className="auth-panel login-card" onSubmit={handleSignIn}>
      <div className="login-heading">
        <p className="context-label">Doctor portal</p>
        <h2 id="sign-in-heading">Welcome back</h2>
        <p>Sign in to review your monitored synthetic patient cohort.</p>
      </div>

      <div className="field-group">
        <label htmlFor="email">Email address</label>
        <input autoComplete="email" disabled={!authChecked || working} id="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
      </div>
      <div className="field-group">
        <label htmlFor="password">Password</label>
        <input autoComplete="current-password" disabled={!authChecked || working} id="password" minLength={6} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
      </div>

      {message && <p className="error-message" role="alert">{message}</p>}
      <button className="primary-button primary-button--full" disabled={!authChecked || working} type="submit">
        {working ? "Signing in..." : "Sign in"}
      </button>
      <p className="form-note">Access is limited to approved doctor accounts.</p>
    </form>
  );
}
