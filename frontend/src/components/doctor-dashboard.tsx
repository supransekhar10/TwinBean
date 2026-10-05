import Link from "next/link";
import type { DashboardPatient } from "@/lib/api";

type DashboardProps = { rows: DashboardPatient[]; loading?: boolean; error?: "general" | "unauthorized" | "unavailable"; onRetry?: () => void };
const ruleLabels = { criteria_met: "Criteria met", criteria_not_met: "Criteria not met", insufficient_creatinine_history: "Insufficient creatinine history" };
const warningLabels: Record<string, string> = { iot_data_stale: "Simulated IoT data is stale.", iot_data_missing: "Simulated IoT data is missing.", missing_iot_window: "A complete simulated IoT window is unavailable.", no_stored_prediction: "No valid stored prediction is available.", model_engine_unavailable: "The research prediction model is unavailable." };

function warningText(row: DashboardPatient): string | null {
  const codes = [...row.prediction.warnings, ...(row.prediction.status === "unavailable" ? row.prediction.reasons : [])];
  return codes.length ? warningLabels[codes[0]] ?? "Prediction data needs review." : null;
}
function generatedAt(row: DashboardPatient): string {
  if (!row.prediction.generated_at) return "Not available";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(row.prediction.generated_at)) + " UTC";
}
function riskText(row: DashboardPatient): string {
  return row.prediction.status === "available" ? `${Math.round(row.prediction.probability * 100)}%` : "Risk unavailable";
}

function PatientFacts({ row }: { row: DashboardPatient }) {
  const warning = warningText(row);
  return <>
    <div className="patient-identity"><strong title={row.patient.display_name}>{row.patient.display_name}</strong><span>Age {row.patient.age} / CKD stage {row.patient.ckd_stage}</span></div>
    <div className="risk-region" aria-label="Future 24-hour AKI risk"><span className="data-label">24-hour AKI risk</span><strong>{riskText(row)}</strong></div>
    <div><span className="data-label">Prediction generated</span><span className="tabular">{generatedAt(row)}</span></div>
    <div className={warning ? "quality-warning" : "quality-clear"}><span className="data-label">Data quality</span><span>{warning ?? "No warnings"}</span></div>
    <div className="rule-region" aria-label="Current clinical rule"><span className="data-label">Current clinical rule</span><strong>{row.current_rule ? ruleLabels[row.current_rule.status] : "Insufficient creatinine history"}</strong></div>
  </>;
}

export function DoctorDashboard({ rows, loading = false, error, onRetry }: DashboardProps) {
  if (loading) return <section className="dashboard-state" aria-live="polite"><h2>Loading monitored patients...</h2><div className="dashboard-skeleton" aria-hidden="true" /></section>;
  if (error) {
    const content = error === "unauthorized"
      ? ["Doctor access is required", "Sign out and sign in with an approved doctor account, then refresh the role token."]
      : error === "unavailable"
        ? ["Patient data is temporarily unavailable", "Firestore could not complete the request. Your doctor access is still valid; retry shortly."]
        : ["Patient dashboard could not be loaded", "Check the backend connection and retry."];
    return <section className="dashboard-state" role="alert"><h2>{content[0]}</h2><p>{content[1]}</p>{onRetry && <button className="secondary-button" onClick={onRetry} type="button">Retry dashboard</button>}</section>;
  }
  if (!rows.length) return <section className="dashboard-state"><h2>No monitored patients available</h2><p>No synthetic patients are in the active cohort. Refresh the dashboard or ask the prototype administrator to confirm the cohort.</p>{onRetry && <button className="secondary-button" onClick={onRetry} type="button">Refresh dashboard</button>}</section>;
  return <section className="dashboard" aria-labelledby="patient-list-heading">
    <div className="dashboard-heading"><div><p className="context-label">Active synthetic cohort</p><h2 id="patient-list-heading">Risk-prioritized monitored patients</h2><p>Valid forecasts are ordered by highest predicted 24-hour AKI risk. Every monitored patient remains accessible.</p></div><strong aria-live="polite">{rows.length} monitored {rows.length === 1 ? "patient" : "patients"}</strong></div>
    <div className="desktop-dashboard"><table><caption>Risk-prioritized monitored patients</caption><thead><tr><th>Patient</th><th>Current clinical rule</th><th>24-hour AKI risk</th><th>Prediction generated</th><th>Data quality</th><th>Open</th></tr></thead><tbody>{rows.map((row) => <tr key={row.patient.patient_id}><td><div className="patient-identity"><strong title={row.patient.display_name}>{row.patient.display_name}</strong><span>Age {row.patient.age} / CKD stage {row.patient.ckd_stage}</span></div></td><td><div className="rule-region" aria-label="Current clinical rule"><strong>{row.current_rule ? ruleLabels[row.current_rule.status] : "Insufficient creatinine history"}</strong></div></td><td><div className="risk-region" aria-label="Future 24-hour AKI risk"><strong>{riskText(row)}</strong></div></td><td className="tabular">{generatedAt(row)}</td><td>{warningText(row) ? <span className="quality-warning"><span className="data-label">Data quality warning</span>{warningText(row)}</span> : "No warnings"}</td><td><Link className="open-patient" href={`/patients/${row.patient.patient_id}`} aria-label={`Open patient ${row.patient.display_name}`}>Open patient</Link></td></tr>)}</tbody></table></div>
    <ol className="mobile-dashboard">{rows.map((row) => <li key={row.patient.patient_id}><PatientFacts row={row} /><Link className="open-patient" href={`/patients/${row.patient.patient_id}`} aria-label={`Open patient ${row.patient.display_name}`}>Open patient</Link></li>)}</ol>
  </section>;
}
