import { mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { chromium } from "playwright-core";

const baseUrl = process.env.TWINBEAN_FRONTEND_URL ?? "http://127.0.0.1:3000";
const executablePath = process.env.EDGE_PATH ??
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const reviewDir = path.resolve(process.cwd(), "..", ".impeccable", "review");
const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "laptop", width: 1024, height: 900 },
  { name: "desktop", width: 1440, height: 1000 },
];
const selectors = [
  ".page-shell",
  ".product-bar",
  ".prototype-label",
  ".content-grid",
  ".intro-copy",
  ".lede",
  ".auth-panel",
  ".page-footer",
];
const dashboardSelectors = [
  ".dashboard-shell",
  ".clinician-sidebar",
  ".sidebar-nav",
  ".dashboard-content",
  ".dashboard-intro",
  ".dashboard",
  ".dashboard-heading",
  ".desktop-dashboard",
  ".mobile-dashboard",
  ".open-patient",
];

await mkdir(reviewDir, { recursive: true });
const browser = await chromium.launch({ executablePath, headless: true });
let failed = false;

try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    const loginResult = await page.evaluate((checkedSelectors) => {
      const elements = checkedSelectors.map((selector) => {
        const element = document.querySelector(selector);
        if (!element) return { selector, missing: true };
        const rect = element.getBoundingClientRect();
        return { selector, left: rect.left, right: rect.right, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, overflowsViewport: rect.left < -0.5 || rect.right > innerWidth + 0.5, overflowsContainer: element.scrollWidth > element.clientWidth + 1 };
      });
      return { documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth, elements };
    }, selectors);
    await page.evaluate(() => {
      document.body.innerHTML = `<main class="dashboard-shell"><aside class="clinician-sidebar"><a class="sidebar-brand" href="#"><span class="wordmark-mark">TB</span><div><strong>TwinBean</strong><span>Kidney digital twin</span></div></a><nav class="sidebar-nav"><a class="sidebar-link sidebar-link--overview" href="#">Overview</a><a class="sidebar-link sidebar-link--patients sidebar-link--active" href="#">Monitored patients</a><a class="sidebar-link sidebar-link--reviews" href="#">Review workspace</a><a class="sidebar-link sidebar-link--reports" href="#">Patient reports</a><a class="sidebar-link sidebar-link--assistant" href="#">Twini assistant</a><button class="sidebar-link sidebar-link--refresh">Refresh Data</button></nav><div class="sidebar-account"><span>Signed in as</span><strong>doctor.demo@example.com</strong><button class="sidebar-signout">Sign out</button></div></aside><div class="dashboard-content"><section class="dashboard-intro"><div><p class="context-label">Doctor dashboard</p><h1>Monitored patients</h1><p>Review current clinical evidence and future 24-hour AKI risk as separate signals.</p></div><span class="prototype-label">Research prototype / synthetic data only</span></section><section class="dashboard" aria-labelledby="patient-list-heading"><div class="dashboard-heading"><div><p class="context-label">Active synthetic cohort</p><h2 id="patient-list-heading">Risk-prioritized monitored patients</h2><p>Valid forecasts are ordered by highest predicted 24-hour AKI risk. Every monitored patient remains accessible.</p></div><strong>2 monitored patients</strong></div><div class="desktop-dashboard"><table><caption>Risk-prioritized monitored patients</caption><thead><tr><th>Patient</th><th>Current clinical rule</th><th>Clinical priority</th><th>24-hour AKI risk</th><th>Prediction generated</th><th>Open</th></tr></thead><tbody><tr><td><div class="patient-identity"><strong>A very long synthetic patient name used to verify safe wrapping</strong><span>Age 71 / CKD stage G4</span></div></td><td>Criteria not met</td><td>High predicted risk</td><td><div class="risk-region"><strong>82%</strong></div></td><td>Oct 5, 2026, 8:01 AM UTC</td><td><a class="open-patient" href="#">Open patient</a></td></tr></tbody></table></div><ol class="mobile-dashboard"><li><div class="patient-identity"><strong>A very long synthetic patient name used to verify safe wrapping</strong><span>Age 63 / CKD stage G3b</span></div><div class="rule-region"><span class="data-label">Current clinical rule</span><strong>Criteria met</strong></div><div class="priority priority--urgent"><span class="data-label">Clinical priority</span><strong>Review now</strong></div><div class="risk-region"><span class="data-label">24-hour AKI risk</span><strong>82%</strong></div><div><span class="data-label">Prediction generated</span><span>Oct 5, 2026, 8:01 AM UTC</span></div><a class="open-patient" href="#">Open patient</a></li></ol></section></div></main>`;
    });

    const result = await page.evaluate((checkedSelectors) => {
      const documentWidth = document.documentElement.scrollWidth;
      const viewportWidth = document.documentElement.clientWidth;
      const elements = checkedSelectors.map((selector) => {
        const element = document.querySelector(selector);
        if (!element) return { selector, missing: true };
        const rect = element.getBoundingClientRect();
        return {
          selector,
          left: Math.round(rect.left * 100) / 100,
          right: Math.round(rect.right * 100) / 100,
          width: Math.round(rect.width * 100) / 100,
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
          overflowsViewport: rect.left < -0.5 || rect.right > window.innerWidth + 0.5,
          overflowsContainer: element.scrollWidth > element.clientWidth + 1,
        };
      });
      return { documentWidth, viewportWidth, elements };
    }, dashboardSelectors);

    await page.screenshot({
      path: path.join(reviewDir, `${viewport.name}.png`),
      fullPage: true,
    });

    const twiniResult = await page.evaluate(() => {
      document.body.insertAdjacentHTML("beforeend", `<aside class="twini-drawer is-open has-context" aria-label="Twini assistant panel"><header><div><span>Project-grounded assistant</span><h2>Twini</h2></div><button>×</button></header><div class="twini-drawer-context"><strong>Patient context active</strong><span>Answers can reference this synthetic patient record.</span></div><div class="twini-drawer-thread"><article class="twini-drawer-message is-assistant"><span>Twini</span><div class="twini-answer"><h3>What you are looking at</h3><p>A concise project-grounded summary.</p><div class="twini-answer-records"><section><div><strong>Piece</strong><p>Milestone roadmap with an intentionally long but readable name</p></div><div><strong>What it is</strong><p>The development plan for TwinBean.</p></div><div><strong>Key points</strong><p>Clinical rules, future predictions, and SHAP explanations remain separate.</p></div></section></div></div></article></div><form class="twini-drawer-composer"><label>Ask Twini</label><textarea placeholder="Type your question..."></textarea><button>Send</button><small>Synthetic research support, not diagnosis or treatment guidance.</small></form></aside>`);
      const checkedSelectors = [".twini-drawer", ".twini-drawer-thread", ".twini-drawer-message", ".twini-answer-records"];
      const elements = checkedSelectors.map((selector) => {
        const element = document.querySelector(selector);
        const rect = element.getBoundingClientRect();
        return { selector, left: rect.left, right: rect.right, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, overflowsViewport: rect.left < -0.5 || rect.right > innerWidth + 0.5, overflowsContainer: element.scrollWidth > element.clientWidth + 1 };
      });
      return { documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth, elements };
    });

    const offenders = [...loginResult.elements, ...result.elements, ...twiniResult.elements].filter(
      (item) => item.missing || item.overflowsViewport || item.overflowsContainer,
    );
    const viewportPass = loginResult.documentWidth <= loginResult.viewportWidth + 1 && result.documentWidth <= result.viewportWidth + 1 && twiniResult.documentWidth <= twiniResult.viewportWidth + 1 && offenders.length === 0;
    console.log(JSON.stringify({ viewport, login: loginResult, dashboard: result, twini: twiniResult, offenders, pass: viewportPass }));
    failed ||= !viewportPass;
    await page.close();
  }
} finally {
  await browser.close();
}

if (failed) process.exit(1);
