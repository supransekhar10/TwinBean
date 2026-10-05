---
status: resolved
trigger: "Dashboard and patient detail remain in loading state for too long."
created: 2026-10-05
updated: 2026-10-05
---

## Current Focus

- hypothesis: confirmed
- test: Exercise Firestore under exhausted/unavailable service conditions.
- expecting: Requests leave loading state within a bounded interval.
- next_action: none

## Evidence

- timestamp: 2026-10-05T22:40:00+05:30
  result: Firestore SDK retried a failed pointer read until a deadline, while browser fetches had no abort timeout.

## Resolution

- root_cause: Unbounded browser requests combined with long Firestore transport retries kept UI state at loading.
- fix: Interactive Firestore reads use a three-second RPC timeout with no SDK retry; browser API requests abort after eight seconds and show a retryable unavailable state.
- verification: 43 backend tests and 10 frontend tests passed; ESLint and production build passed; frontend and backend health returned 200.
- files_changed: [backend/app/main.py, backend/app/patients.py, backend/tests/test_dashboard_routes.py, backend/tests/test_patient_routes.py, backend/tests/test_patients.py, frontend/src/lib/api.ts, frontend/src/lib/api.test.ts, frontend/src/components/dashboard-screen.tsx, frontend/src/components/doctor-dashboard.tsx, frontend/src/components/doctor-dashboard.test.tsx]
