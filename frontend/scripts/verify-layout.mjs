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
    await page.evaluate(() => {
      const grid = document.querySelector(".content-grid");
      if (!grid) return;
      grid.innerHTML = `<div class="doctor-workspace"><section class="auth-panel auth-panel--compact"><h2>Doctor access check</h2></section><section class="dashboard" aria-labelledby="patient-list-heading"><div class="dashboard-heading"><div><p class="context-label">Active synthetic cohort</p><h2 id="patient-list-heading">Risk-prioritized monitored patients</h2><p>Valid forecasts are ordered by highest predicted 24-hour AKI risk. Every monitored patient remains accessible.</p></div><strong>2 monitored patients</strong></div><div class="desktop-dashboard"><table><caption>Risk-prioritized monitored patients</caption><thead><tr><th>Patient</th><th>Current clinical rule</th><th>24-hour AKI risk</th><th>Prediction generated</th><th>Data quality</th><th>Open</th></tr></thead><tbody><tr><td><div class="patient-identity"><strong>A very long synthetic patient name used to verify safe wrapping</strong><span>Age 71 / CKD stage G4</span></div></td><td>Criteria not met</td><td><div class="risk-region"><strong>82%</strong></div></td><td>Oct 5, 2026, 8:01 AM UTC</td><td><span class="quality-warning">Simulated IoT data is stale and requires review before navigation.</span></td><td><a class="open-patient" href="#">Open patient</a></td></tr></tbody></table></div><ol class="mobile-dashboard"><li><div class="patient-identity"><strong>A very long synthetic patient name used to verify safe wrapping</strong><span>Age 63 / CKD stage G3b</span></div><div class="risk-region"><span class="data-label">24-hour AKI risk</span><strong>Risk unavailable</strong></div><div><span class="data-label">Prediction generated</span><span>Not available</span></div><div class="quality-warning"><span class="data-label">Data quality</span>No valid stored prediction is available.</div><div class="rule-region"><span class="data-label">Current clinical rule</span><strong>Insufficient creatinine history</strong></div><a class="open-patient" href="#">Open patient</a></li></ol></section></div>`;
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
    }, [...selectors.filter((selector) => ![".intro-copy", ".lede"].includes(selector)), ...dashboardSelectors]);

    await page.screenshot({
      path: path.join(reviewDir, `${viewport.name}.png`),
      fullPage: true,
    });

    const offenders = result.elements.filter(
      (item) => item.missing || item.overflowsViewport || item.overflowsContainer,
    );
    const viewportPass = result.documentWidth <= result.viewportWidth + 1 && offenders.length === 0;
    console.log(JSON.stringify({ viewport, ...result, offenders, pass: viewportPass }));
    failed ||= !viewportPass;
    await page.close();
  }
} finally {
  await browser.close();
}

if (failed) process.exit(1);
