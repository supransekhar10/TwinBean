---
status: resolved
trigger: "Doctor sign-in could not complete while the backend failed to start under Windows Application Control."
created: 2026-10-05
updated: 2026-10-05
---

## Current Focus

- hypothesis: confirmed
- test: Start FastAPI with the repository virtual environment and call health endpoints.
- expecting: startup does not import pandas, SHAP, or XGBoost.
- next_action: none

## Evidence

- timestamp: 2026-10-05T07:15:00+05:30
  result: Attached traceback showed pandas `ccalendar` DLL blocked while importing `app.main`; no process was listening on port 8000.

## Resolution

- root_cause: The prediction module eagerly imported the native ML stack during FastAPI startup, although login and stored-patient reads do not require it.
- fix: Deferred native ML imports until explicit inference and fail closed to an unavailable prediction if the host blocks the ML runtime.
- verification: 14 focused startup/auth/dashboard tests passed; the exact virtual-environment Uvicorn command started successfully; public health returned 200 and protected health without a token returned 401.
- files_changed: [backend/app/prediction_service.py, backend/tests/test_health.py]
