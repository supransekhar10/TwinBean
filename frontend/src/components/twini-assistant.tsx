"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";

import { askTwini, fetchDoctorDashboard, type DashboardPatient, type TwiniMessage } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";
import { ClinicianSidebar } from "./clinician-sidebar";
import { TwiniAnswer } from "./twini-answer";

type DisplayMessage = TwiniMessage & { citations?: Array<{ source: string; label: string }> };

const starters = [
  "Explain how TwinBean keeps clinical rules separate from future risk.",
  "What do creatinine, eGFR, and SHAP mean in this prototype?",
  "How was the synthetic AKI model evaluated without future-data leakage?",
];

export function TwiniAssistant() {
  const router = useRouter();
  const questionRef = useRef<HTMLTextAreaElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const [user, setUser] = useState<User | null>(null);
  const [patients, setPatients] = useState<DashboardPatient[]>([]);
  const [patientId, setPatientId] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<"ready" | "sending" | "error">("ready");
  const [error, setError] = useState("");
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [refreshing, setRefreshing] = useState(false);

  const loadPatients = useCallback(async (activeUser: User, initial = false) => {
    if (initial) setLoadState("loading");
    try {
      setPatients(await fetchDoctorDashboard(await activeUser.getIdToken(), !initial));
      setLoadState("ready");
    } catch {
      if (initial) setLoadState("error");
    }
  }, []);

  useEffect(() => onAuthStateChanged(firebaseAuth, (activeUser) => {
    if (!activeUser) { router.replace("/"); return; }
    setUser(activeUser);
    void loadPatients(activeUser, true);
  }), [loadPatients, router]);

  const refreshPatients = useCallback(async () => {
    if (!user || refreshing) return;
    setRefreshing(true);
    try { await loadPatients(user); }
    finally { setRefreshing(false); }
  }, [loadPatients, refreshing, user]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, state]);

  if (loadState === "loading") {
    return null;
  }

  if (loadState === "error") {
    return <main className="dashboard-shell"><ClinicianSidebar active="assistant" email={user?.email} onRefresh={refreshPatients} refreshing={refreshing} /><div className="dashboard-content"><section className="dashboard-state"><h1>Twini could not load patient context</h1><p>Refresh data or check the backend connection before continuing.</p></section></div></main>;
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const cleaned = question.trim();
    if (!cleaned || !user || state === "sending") return;
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, { role: "user", content: cleaned }]);
    setQuestion("");
    setState("sending");
    setError("");
    try {
      const result = await askTwini(cleaned, patientId || null, history, await user.getIdToken());
      setMessages((current) => [...current, { role: "assistant", content: result.answer, citations: result.citations }]);
      setState("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Twini could not answer right now.");
      setState("error");
    }
  }

  function chooseStarter(starter: string) {
    setQuestion(starter);
    questionRef.current?.focus();
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return <main className="dashboard-shell">
    <ClinicianSidebar active="assistant" email={user?.email} onRefresh={refreshPatients} refreshing={refreshing} />
    <div className="dashboard-content twini-page">
      <section className="dashboard-intro twini-intro">
        <div><p className="context-label">Project-grounded assistant</p><h1>Meet Twini</h1><p>Explore TwinBean evidence, kidney terminology, and authorized synthetic patient records.</p></div>
        <div className="twini-status"><span className="twini-status-logo"><Image src="/twinbean-logo.png" alt="" width={44} height={44} /></span><strong>Patient-aware support</strong><small>Groq-powered. No chat history stored.</small></div>
      </section>

      <section className="twini-workspace" aria-label="Twini assistant">
        <aside className="twini-guide" aria-label="Twini capabilities">
          <div className="twini-guide-title"><span className="twini-drawer-avatar"><Image src="/twinbean-logo.png" alt="" width={34} height={34} /></span><div><h2>Twini</h2><p>TwinBean AI assistant</p></div></div>
          <div className="twini-guide-copy"><strong>Built for evidence review</strong><p>Twini keeps current rules, future predictions, and SHAP explanations separate.</p></div>
          <nav aria-label="Suggested questions">{starters.map((starter, index) => <button key={starter} type="button" onClick={() => chooseStarter(starter)}><span>{String(index + 1).padStart(2, "0")}</span>{starter}</button>)}</nav>
          <small>Educational support only. Verify important information against the displayed evidence.</small>
        </aside>

        <div className="twini-conversation">
          <header className="twini-toolbar">
            <div><h2>Conversation</h2><p>{patientId ? "Patient context is active." : "Project knowledge is active."}</p></div>
            <label><span>Patient context</span><select value={patientId} onChange={(event) => setPatientId(event.target.value)}><option value="">Project knowledge only</option>{patients.map((row) => <option key={row.patient.patient_id} value={row.patient.patient_id}>{row.patient.display_name} / CKD {row.patient.ckd_stage}</option>)}</select></label>
          </header>

          <div className="twini-thread" aria-live="polite" ref={threadRef}>
            {messages.length === 0 ? <div className="twini-empty"><span className="twini-drawer-avatar"><Image src="/twinbean-logo.png" alt="" width={32} height={32} /></span><div><strong>Hello. What would you like to review?</strong><p>I can explain TwinBean or use the selected synthetic patient as context. Sources stay visible with the answer.</p></div></div> : messages.map((message, index) => <article className={`twini-message twini-message--${message.role}`} key={`${message.role}-${index}`}><span>{message.role === "assistant" ? "Twini" : "You"}</span>{message.role === "assistant" ? <TwiniAnswer content={message.content} /> : <p>{message.content}</p>}{message.citations?.length ? <ul aria-label="Sources">{message.citations.map((citation) => <li key={`${citation.source}-${citation.label}`}>{citation.label}</li>)}</ul> : null}</article>)}
            {state === "sending" && <div className="twini-thinking"><span /><span /><span /><strong>Twini is reviewing the evidence</strong></div>}
          </div>

          <form className="twini-composer" onSubmit={submit}>
            <label htmlFor="twini-question">Ask Twini</label>
            <div><textarea id="twini-question" maxLength={2000} onChange={(event) => setQuestion(event.target.value)} onKeyDown={submitOnEnter} placeholder="Ask about TwinBean or the selected synthetic patient..." ref={questionRef} rows={1} value={question} /><button className="primary-button" disabled={!question.trim() || state === "sending"} type="submit">{state === "sending" ? "Reviewing..." : "Send"}</button></div>
            {error && <p className="error-message" role="alert">{error}</p>}
            <small>Press Enter to send. Use Shift + Enter for a new line.</small>
          </form>
        </div>
      </section>
    </div>
  </main>;
}
