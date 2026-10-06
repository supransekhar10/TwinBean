import { AuthPanel } from "@/components/auth-panel";
import Image from "next/image";

export default function Home() {
  return (
    <main className="page-shell">
      <header className="product-bar">
        <a className="wordmark" href="#main-content" aria-label="TwinBean home">
          <Image className="login-wordmark-logo" src="/twinbean-logo.png" alt="" width={42} height={42} priority />
          <span>TwinBean</span>
        </a>
        <span className="prototype-label">Research prototype / synthetic data only</span>
      </header>

      <a className="skip-link" href="#main-content">Skip to sign in</a>
      <div className="content-grid" id="main-content">
        <section className="intro-copy" aria-labelledby="page-title">
          <p className="context-label">Kidney digital twin research</p>
          <h1 id="page-title">Kidney evidence, organized for clinical review.</h1>
          <p className="lede">
            Review a synthetic CKD cohort through longitudinal EHR history, simulated
            home-monitoring trends, current clinical rules, and clearly separated 24-hour AKI predictions.
          </p>
          <div className="login-capabilities" aria-label="TwinBean clinical workflow"><div><strong>Review</strong><span>Longitudinal synthetic EHR and simulated home-monitoring trends</span></div><div><strong>Prioritize</strong><span>Current creatinine criteria without confusing them with future risk</span></div><div><strong>Document</strong><span>Doctor review notes stored separately from generated evidence</span></div></div>
          <div className="login-assurance"><strong>Designed for honest interpretation</strong><span>Invalid predictions remain “Risk unavailable.” Clinical rules, forecasts, and SHAP explanations are never merged.</span></div>
        </section>

        <AuthPanel />
      </div>

      <footer className="page-footer">
        <span>Secure doctor access</span>
        <span>Not for clinical use</span>
      </footer>
    </main>
  );
}
