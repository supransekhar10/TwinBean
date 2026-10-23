"use client";

import { useState } from "react";
import { downloadPatientReport } from "../lib/api";
import { firebaseAuth } from "../lib/firebase";

export function DownloadReportButton({ patientId, patientName, compact = false }: { patientId: string; patientName: string; compact?: boolean }) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  async function download() {
    const user = firebaseAuth.currentUser;
    if (!user) return;
    setState("loading");
    try {
      const blob = await downloadPatientReport(patientId, await user.getIdToken());
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `twinbean-${patientName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}-report.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      setState("idle");
    } catch { setState("error"); }
  }
  return <div className={`report-download${compact ? " report-download--compact" : ""}`}><button className={compact ? "secondary-button" : "primary-button"} disabled={state === "loading"} onClick={download} type="button">{state === "loading" ? "Preparing PDF..." : "Download PDF report"}</button>{state === "error" && <span role="alert">PDF could not be generated. Retry shortly.</span>}</div>;
}
