"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { DashboardPatient } from "@/lib/api";

type DashboardProps = { rows: DashboardPatient[]; loading?: boolean; error?: "general" | "unauthorized" | "unavailable"; onRetry?: () => void };
type PatientFilter = "all" | "criteria_met" | "risk_available" | "risk_unavailable";
const ruleLabels = { criteria_met: "Criteria met", criteria_not_met: "Criteria not met", insufficient_creatinine_history: "Insufficient creatinine history" };

function generatedAt(row: DashboardPatient): string {
  if (!row.prediction.generated_at) return "Not available";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(row.prediction.generated_at)) + " UTC";
}

function riskText(row: DashboardPatient): string {
  return row.prediction.status === "available" ? `${Math.round(row.prediction.probability * 100)}%` : "Risk unavailable";
}

function priorityText(row: DashboardPatient): string {
  if (row.current_rule?.status === "criteria_met") return "Review now";
  if (row.prediction.status === "available" && row.prediction.probability >= 0.7) return "High predicted risk";
  return "Monitor";
}

function PatientFacts({ row }: { row: DashboardPatient }) {
  const priority = priorityText(row);
  return <>
    <div className="patient-identity"><strong title={row.patient.display_name}>{row.patient.display_name}</strong><span>Age {row.patient.age}{row.patient.sex ? ` / ${row.patient.sex}` : ""} / CKD stage {row.patient.ckd_stage}</span>{row.patient.ckd_context && <span>{row.patient.ckd_context}</span>}</div>
    <div className="rule-region" aria-label="Current clinical rule"><span className="data-label">Current clinical rule</span><strong>{row.current_rule ? ruleLabels[row.current_rule.status] : "Insufficient creatinine history"}</strong></div>
    <div className={priority === "Review now" ? "priority priority--urgent" : "priority"}><span className="data-label">Clinical priority</span><strong>{priority}</strong></div>
    <div className="risk-region" aria-label="Future 24-hour AKI risk"><span className="data-label">24-hour AKI risk</span><strong>{riskText(row)}</strong></div>
    <div><span className="data-label">Prediction generated</span><span className="tabular">{generatedAt(row)}</span></div>
  </>;
}

export function DoctorDashboard({ rows, loading = false, error, onRetry }: DashboardProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<PatientFilter>("all");
  const criteriaMet = rows.filter((row) => row.current_rule?.status === "criteria_met").length;
  const availablePredictions = rows.filter((row) => row.prediction.status === "available").length;
  const filteredRows = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return rows.filter((row) => {
      const matchesQuery = !term || `${row.patient.display_name} ${row.patient.ckd_stage} ${row.patient.ckd_context ?? ""}`.toLocaleLowerCase().includes(term);
      const matchesFilter = filter === "all"
        || (filter === "criteria_met" && row.current_rule?.status === "criteria_met")
        || (filter === "risk_available" && row.prediction.status === "available")
        || (filter === "risk_unavailable" && row.prediction.status === "unavailable");
      return matchesQuery && matchesFilter;
    }).sort((left, right) => {
      if (left.prediction.status === "available" && right.prediction.status === "available") return right.prediction.probability - left.prediction.probability;
      if (left.prediction.status === "available") return -1;
      if (right.prediction.status === "available") return 1;
      return Number(right.current_rule?.status === "criteria_met") - Number(left.current_rule?.status === "criteria_met");
    });
  }, [filter, query, rows]);

  if (loading) return <section className="dashboard-state" aria-live="polite"><h2>Loading monitored patients...</h2><div className="dashboard-skeleton" aria-hidden="true" /></section>;
  if (error) {
    const content = error === "unauthorized"
      ? ["Doctor access is required", "Sign out and sign in with an approved doctor account."]
      : error === "unavailable"
        ? ["Patient data is temporarily unavailable", "Firestore could not complete the request. Your doctor access is still valid; retry shortly."]
        : ["Patient dashboard could not be loaded", "Check the backend connection and retry."];
    return <section className="dashboard-state" role="alert"><h2>{content[0]}</h2><p>{content[1]}</p>{onRetry && <button className="secondary-button" onClick={onRetry} type="button">Retry dashboard</button>}</section>;
  }
  if (!rows.length) return <section className="dashboard-state"><h2>No monitored patients available</h2><p>No synthetic patients are in the active cohort.</p>{onRetry && <button className="secondary-button" onClick={onRetry} type="button">Refresh dashboard</button>}</section>;

  return <section className="dashboard" aria-labelledby="patient-list-heading">
    <div className="dashboard-heading"><div><h2 id="patient-list-heading">Risk-prioritized monitored patients</h2><p>Current clinical rules and future 24-hour AKI risk remain separate. Synthetic patients meeting current creatinine criteria are marked for review.</p></div><strong aria-live="polite">{filteredRows.length} shown</strong></div>
    <div className="dashboard-overview" aria-label="Cohort summary">
      <div><strong>{rows.length}</strong><span>Monitored patients</span></div>
      <div className="overview-urgent"><strong>{criteriaMet}</strong><span>Current criteria met</span></div>
      <div><strong>{availablePredictions}</strong><span>Predictions available</span></div>
    </div>
    <div className="dashboard-controls">
      <label><span>Search patients</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or CKD stage" /></label>
      <label><span>Show</span><select value={filter} onChange={(event) => setFilter(event.target.value as PatientFilter)}><option value="all">All patients</option><option value="criteria_met">Current criteria met</option><option value="risk_available">Prediction available</option><option value="risk_unavailable">Risk unavailable</option></select></label>
    </div>
    {!filteredRows.length ? <div className="dashboard-empty"><h3>No matching patients</h3><p>Change the search or filter to view the full monitored cohort.</p></div> : <>
      <div className="desktop-dashboard"><table><caption>Risk-prioritized monitored patients</caption><thead><tr><th>Patient</th><th>Current clinical rule</th><th>Clinical priority</th><th>24-hour AKI risk</th><th>Prediction generated</th><th>Open</th></tr></thead><tbody>{filteredRows.map((row) => { const priority = priorityText(row); return <tr className={priority === "Review now" ? "row-urgent" : undefined} key={row.patient.patient_id}><td><div className="patient-identity"><strong title={row.patient.display_name}>{row.patient.display_name}</strong><span>Age {row.patient.age}{row.patient.sex ? ` / ${row.patient.sex}` : ""} / CKD stage {row.patient.ckd_stage}</span>{row.patient.ckd_context && <span>{row.patient.ckd_context}</span>}</div></td><td><div className="rule-region" aria-label="Current clinical rule"><strong>{row.current_rule ? ruleLabels[row.current_rule.status] : "Insufficient creatinine history"}</strong></div></td><td><span className={priority === "Review now" ? "priority priority--urgent" : "priority"}>{priority}</span></td><td><div className="risk-region" aria-label="Future 24-hour AKI risk"><strong>{riskText(row)}</strong></div></td><td className="tabular">{generatedAt(row)}</td><td><Link className="open-patient" href={`/patients/${row.patient.patient_id}`} aria-label={`Open patient ${row.patient.display_name}`}>Open patient</Link></td></tr>; })}</tbody></table></div>
      <ol className="mobile-dashboard">{filteredRows.map((row) => <li className={row.current_rule?.status === "criteria_met" ? "row-urgent" : undefined} key={row.patient.patient_id}><PatientFacts row={row} /><Link className="open-patient" href={`/patients/${row.patient.patient_id}`} aria-label={`Open patient ${row.patient.display_name}`}>Open patient</Link></li>)}</ol>
    </>}
  </section>;
}
