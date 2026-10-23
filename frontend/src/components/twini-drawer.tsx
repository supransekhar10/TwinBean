"use client";

import { onAuthStateChanged, type User } from "@firebase/auth";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { askTwini, type TwiniMessage } from "@/lib/api";
import { firebaseAuth } from "@/lib/firebase";
import { TwiniAnswer } from "./twini-answer";

type DrawerMessage = TwiniMessage & { citations?: Array<{ source: string; label: string }> };

const patientStarters = [
  "Explain this patient's current evidence.",
  "Summarize the 24-hour AKI prediction.",
  "What does the SHAP explanation show?",
];

export function TwiniDrawer() {
  const pathname = usePathname();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const [user, setUser] = useState<User | null>(null);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<DrawerMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const patientId = /^\/patients\/(tbp-[0-9a-f]{32})$/.exec(pathname)?.[1] ?? null;

  useEffect(() => onAuthStateChanged(firebaseAuth, setUser), []);
  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        launcherRef.current?.focus();
      }
      if (event.key === "Tab") {
        const focusable = drawerRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href]");
        if (!focusable?.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open, sending]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cleaned = question.trim();
    if (!cleaned || !user || sending) return;
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, { role: "user", content: cleaned }]);
    setQuestion("");
    setSending(true);
    setError("");
    try {
      const response = await askTwini(cleaned, patientId, history, await user.getIdToken());
      setMessages((current) => [...current, { role: "assistant", content: response.answer, citations: response.citations }]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Twini could not answer right now.");
    } finally {
      setSending(false);
    }
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function closeDrawer() {
    setOpen(false);
    launcherRef.current?.focus();
  }

  if (!user || pathname === "/" || pathname === "/assistant") return null;

  const starters = patientId ? patientStarters : ["How does TwinBean separate current rules from future risk?"];

  return <>
    <button className="twini-launcher" aria-controls="twini-drawer" aria-expanded={open} aria-label="Ask Twini" onClick={() => setOpen((current) => !current)} ref={launcherRef} type="button">
      <Image src="/twinbean-logo.png" alt="" width={30} height={30} />
      <span className="twini-launcher-tooltip" role="tooltip">Ask Twini</span>
    </button>
    <button className={`twini-drawer-scrim${open ? " is-open" : ""}`} aria-label="Close Twini" onClick={closeDrawer} tabIndex={open ? 0 : -1} type="button" />
    <aside className={`twini-drawer${open ? " is-open" : ""}${patientId ? " has-context" : ""}`} id="twini-drawer" aria-hidden={!open} aria-label="Twini assistant panel" aria-modal={open} ref={drawerRef} role="dialog">
      <header className="twini-drawer-header">
        <div className="twini-drawer-identity">
          <span className="twini-drawer-avatar"><Image src="/twinbean-logo.png" alt="" width={34} height={34} /></span>
          <div><h2>Twini</h2><span>TwinBean AI assistant</span></div>
        </div>
        <div className="twini-drawer-actions">
          <Link aria-label="Open full Twini workspace" href="/assistant">Open</Link>
          <button aria-label="Close Twini" onClick={closeDrawer} type="button">Close</button>
        </div>
      </header>
      {patientId && <div className="twini-drawer-context"><strong>Patient context active</strong><span>Answers can reference this synthetic patient record.</span></div>}
      <div className="twini-drawer-thread" aria-live="polite" ref={threadRef}>
        {messages.length === 0 && <div className="twini-drawer-empty">
          <div className="twini-drawer-greeting"><span className="twini-drawer-avatar"><Image src="/twinbean-logo.png" alt="" width={30} height={30} /></span><div><strong>Hi, I am Twini.</strong><p>Ask about TwinBean, kidney terminology, model evidence, or {patientId ? "this synthetic patient" : "project evidence"}.</p></div></div>
          <div className="twini-drawer-prompts" aria-label="Suggested questions">{starters.map((starter) => <button key={starter} onClick={() => { setQuestion(starter); inputRef.current?.focus(); }} type="button">{starter}</button>)}</div>
        </div>}
        {messages.map((message, index) => <article className={`twini-drawer-message is-${message.role}`} key={`${message.role}-${index}`}><span>{message.role === "assistant" ? "Twini" : "You"}</span>{message.role === "assistant" ? <TwiniAnswer compact content={message.content} /> : <p>{message.content}</p>}{message.citations?.length ? <small>{message.citations.map((item) => item.label).join(" / ")}</small> : null}</article>)}
        {sending && <div className="twini-thinking"><span /><span /><span /><strong>Reviewing evidence</strong></div>}
      </div>
      <form className="twini-drawer-composer" onSubmit={submit}>
        <label htmlFor="twini-drawer-question">Ask Twini</label>
        <div className="twini-drawer-input"><textarea id="twini-drawer-question" maxLength={2000} onChange={(event) => setQuestion(event.target.value)} onKeyDown={submitOnEnter} placeholder="Ask me anything..." ref={inputRef} rows={1} value={question} /><button aria-label="Send question" disabled={!question.trim() || sending} type="submit">{sending ? "Wait" : "Send"}</button></div>
        {error && <p role="alert">{error}</p>}
        <small>AI-generated content may be inaccurate. Not for diagnosis or treatment.</small>
      </form>
    </aside>
  </>;
}
