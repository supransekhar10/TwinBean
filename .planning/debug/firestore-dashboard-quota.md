---
status: resolved
trigger: "Authenticated doctor sees protected API available while the patient dashboard cannot be loaded."
created: 2026-10-05
updated: 2026-10-05
---

## Symptoms

- Expected: authenticated doctor sees the Firestore-backed dashboard, or an accurate temporary datastore message.
- Actual: doctor authorization succeeds, while the UI reports that the backend cannot be reached.
- Reproduction: sign in as the approved demo doctor and check protected access.

## Current Focus

- hypothesis: Firestore quota exhaustion is being flattened into a generic connection error.
- test: Direct repository read returns Google Cloud `ResourceExhausted` while both health endpoints remain reachable.
- expecting: API returns an explicit temporary-service response and the UI keeps authorization success separate.
- next_action: none

## Evidence

- timestamp: 2026-10-05T07:00:00+05:30
  result: Direct `list_dashboard_patients` call failed with Firestore HTTP 429 `Quota exceeded`; public health returned 200 and protected health had already succeeded in the browser.

## Resolution

- root_cause: Firestore daily quota exhaustion raised an unhandled `ResourceExhausted`; the client then flattened the dashboard failure into a backend connectivity message and also displayed it in the successful authorization panel.
- fix: Map quota exhaustion to a safe retryable HTTP 503, preserve the backend detail in the API client, and render it only in the dashboard state while keeping doctor authorization successful.
- verification: 106 backend tests and 10 frontend tests passed; ESLint and the Next.js production build passed; restarted frontend and live health probes returned HTTP 200.
- files_changed: [backend/app/main.py, backend/tests/test_dashboard_routes.py, frontend/src/lib/api.ts, frontend/src/lib/api.test.ts, frontend/src/components/auth-panel.tsx, frontend/src/components/doctor-dashboard.tsx, frontend/src/components/doctor-dashboard.test.tsx]
