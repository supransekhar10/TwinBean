import { AuthPanel } from "@/components/auth-panel";

export default function Home() {
  return (
    <main className="page-shell">
      <header className="product-bar">
        <a className="wordmark" href="#main-content" aria-label="TwinBean home">
          <span className="wordmark-mark" aria-hidden="true">TB</span>
          <span>TwinBean</span>
        </a>
        <span className="prototype-label">Research prototype / synthetic data only</span>
      </header>

      <a className="skip-link" href="#patient-list-heading">Skip to patient list</a>
      <div className="content-grid" id="main-content">
        <section className="intro-copy" aria-labelledby="page-title">
          <p className="context-label">Kidney digital twin</p>
          <h1 id="page-title">Monitor simulated kidney risk with evidence kept separate.</h1>
          <p className="lede">
            TwinBean will help doctors review synthetic CKD history, simulated IoT trends,
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
        </section>

        <AuthPanel />
      </div>

      <footer className="page-footer">
        <span>Doctor dashboard</span>
        <span>Not for clinical use</span>
      </footer>
    </main>
  );
}
