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
          <div className="login-hero-brand"><Image src="/twinbean-logo.png" alt="TwinBean kidney digital twin" width={118} height={118} priority /><div><span>Kidney digital twin</span><strong>Research prototype</strong></div></div>
          <h1 id="page-title">Clinical kidney monitoring, built for clear decisions.</h1>
          <p className="lede">
            TwinBean helps doctors review synthetic CKD history, simulated IoT trends,
            current clinical rules, and future AKI risk without merging those signals.
          </p>

          <div className="boundary-list" aria-label="Prototype boundaries">
            <div>
              <p><strong>Doctor-only access</strong><br />Firebase identity plus a trusted server role.</p>
            </div>
            <div>
              <p><strong>Separated evidence</strong><br />Clinical rules and predictions remain distinct.</p>
            </div>
            <div>
              <p><strong>Honest uncertainty</strong><br />Unavailable risk is never presented as zero.</p>
            </div>
          </div>
          <div className="login-capabilities" aria-label="TwinBean clinical workflow"><div><strong>Review</strong><span>Longitudinal synthetic EHR and simulated home-monitoring trends</span></div><div><strong>Prioritize</strong><span>Current creatinine criteria without confusing them with future risk</span></div><div><strong>Document</strong><span>Doctor review notes stored separately from generated evidence</span></div></div>
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
