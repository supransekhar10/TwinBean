---
status: resolved
trigger: "Authenticated doctor dashboard displays Patient dashboard could not be loaded while the backend health endpoint is running."
created: 2026-10-05
updated: 2026-10-05
---

## Symptoms

- Expected: the authenticated doctor dashboard loads quickly from a local synthetic snapshot and can be refreshed from Firestore.
- Actual: the dashboard shows a generic backend connection error and no patients.
- Reproduction: sign in as the approved demo doctor and open `/dashboard` while no disk snapshot exists.

## Current Focus

- hypothesis: confirmed
- test: call `PatientRepository.from_firestore().list_dashboard_patients(100)` directly and inspect the exception and cache directory.
- expecting: an internal retry-policy error or Firestore deadline plus an absent `backend/.cache` directory.
- next_action: none

## Evidence

- timestamp: 2026-10-05T23:25:00+05:30
  result: direct repository call raised `AttributeError: 'NoneType' object has no attribute '_predicate'`; a second call raised `DeadlineExceeded`; `backend/.cache` was absent while both local services were listening.

## Resolution

- root_cause: The installed Firestore client treats explicit `retry=None` as a retry object and can dereference its missing predicate; the backend cache was also empty, so no data remained available when Firestore timed out.
- fix: Use a valid no-retry `Retry` policy, build a deterministic backend-only fallback snapshot with named synthetic patients and both streams, keep predictions explicitly unavailable, and preserve visible cached rows when an explicit Firestore refresh fails.
- verification: 54 focused backend tests and 11 frontend tests passed; ESLint, production build, and Impeccable detector passed. Direct cache read returned 12 patients, 35 EHR and 25 IoT observations for the checked patient. Local frontend/backend returned HTTP 200 and unauthenticated patient access returned 401.
- files_changed: [backend/app/patients.py, backend/scripts/build_local_demo_snapshot.py, backend/tests/test_local_demo_snapshot.py, frontend/src/components/dashboard-screen.tsx, frontend/src/components/doctor-dashboard.tsx, frontend/src/components/patient-detail.tsx, docs/SYNTHETIC_DATA.md]
