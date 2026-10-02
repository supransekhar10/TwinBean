"use client";

import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from "@firebase/auth";
import { FormEvent, useEffect, useState } from "react";

import { fetchDoctorHealth, type DoctorHealth } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";

type RequestState = "idle" | "working" | "success" | "error";

function friendlyAuthError(error: unknown): string {
  if (error instanceof Error && error.message.includes("auth/invalid-credential")) {
    return "Email or password was not accepted. Check the account and try again.";
  }
  return "Sign-in could not be completed. Try again.";
}

function friendlyAccessError(error: unknown): string {
  if (error instanceof Error && error.message.includes("Doctor access is required")) {
    return "This account is not approved as a doctor. Ask an administrator to assign the role, then refresh the role token.";
  }
  if (error instanceof Error && error.message.includes("invalid or expired")) {
    return "Your session has expired. Sign out, then sign in again.";
  }
  return "The protected API could not be reached. Check that the backend is running and try again.";
}

export function AuthPanel() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState("");
  const [health, setHealth] = useState<DoctorHealth | null>(null);

  useEffect(
    () => onAuthStateChanged(firebaseAuth, (nextUser) => {
      setUser(nextUser);
      setAuthReady(true);
      setHealth(null);
      setMessage("");
      setRequestState("idle");
    }),
    [],
  );

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRequestState("working");
    setMessage("");
    try {
      await signInWithEmailAndPassword(firebaseAuth, email, password);
      setPassword("");
      setRequestState("success");
    } catch (error) {
      setMessage(friendlyAuthError(error));
      setRequestState("error");
    }
  }

  async function checkAccess(forceRefresh = false) {
    if (!user) return;
    setRequestState("working");
    setMessage("");
    setHealth(null);
    try {
      const token = await user.getIdToken(forceRefresh);
      setHealth(await fetchDoctorHealth(token));
      setRequestState("success");
    } catch (error) {
      setMessage(friendlyAccessError(error));
      setRequestState("error");
    }
  }

  if (!authReady) {
    return <p className="status-line" role="status">Checking sign-in status...</p>;
  }

  if (user) {
    return (
      <section aria-labelledby="access-heading" className="auth-panel">
        <div className="panel-heading">
          <div>
            <p className="context-label">Authenticated account</p>
            <h2 id="access-heading">Doctor access check</h2>
          </div>
          <span className="status-chip status-chip--signed-in">Signed in</span>
        </div>

        <dl className="identity-row">
          <div>
            <dt>Email</dt>
            <dd>{user.email ?? "Email unavailable"}</dd>
          </div>
          <div>
            <dt>Backend role</dt>
            <dd>{health ? "Doctor verified" : "Not checked"}</dd>
          </div>
        </dl>

        {health && (
          <div className="access-result" role="status">
            <span className="result-mark" aria-hidden="true" />
            <div>
              <strong>Protected API available</strong>
              <p>Firebase token verified with the doctor claim.</p>
            </div>
          </div>
        )}

        {message && <p className="error-message" role="alert">{message}</p>}

        <div className="button-row">
          <button
            className="primary-button"
            disabled={requestState === "working"}
            onClick={() => checkAccess(false)}
            type="button"
          >
            {requestState === "working" ? "Checking access..." : "Check protected API"}
          </button>
          <button
            className="secondary-button"
            disabled={requestState === "working"}
            onClick={() => checkAccess(true)}
            type="button"
          >
            Refresh role token
          </button>
          <button className="text-button" onClick={() => signOut(firebaseAuth)} type="button">
            Sign out
          </button>
        </div>
      </section>
    );
  }

  return (
    <form aria-labelledby="sign-in-heading" className="auth-panel" onSubmit={handleSignIn}>
      <div className="panel-heading">
        <div>
          <p className="context-label">Secure prototype access</p>
          <h2 id="sign-in-heading">Sign in as an approved doctor</h2>
        </div>
        <span className="status-chip">Authorization required</span>
      </div>

      <div className="field-group">
        <label htmlFor="email">Email address</label>
        <input
          autoComplete="email"
          id="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
      </div>

      <div className="field-group">
        <label htmlFor="password">Password</label>
        <input
          autoComplete="current-password"
          id="password"
          minLength={6}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </div>

      {message && <p className="error-message" role="alert">{message}</p>}

      <button className="primary-button primary-button--full" disabled={requestState === "working"} type="submit">
        {requestState === "working" ? "Signing in..." : "Sign in"}
      </button>
      <p className="form-note">Access also requires a server-assigned doctor role.</p>
    </form>
  );
}
