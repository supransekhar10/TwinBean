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

await mkdir(reviewDir, { recursive: true });
const browser = await chromium.launch({ executablePath, headless: true });
let failed = false;

try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    await page.goto(baseUrl, { waitUntil: "networkidle" });

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
    }, selectors);

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
