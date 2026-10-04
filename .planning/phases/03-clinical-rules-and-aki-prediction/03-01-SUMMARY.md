---
phase: 03-clinical-rules-and-aki-prediction
plan: "01"
subsystem: backend clinical-result generation
tags: [fastapi, firestore, pydantic, authorization, aki]
requires:
  - Phase 02 active immutable Firestore cohort repository
provides:
  - Separate, typed current creatinine-rule and 24-hour AKI forecast contracts
  - Doctor-authorized clinical-result generation route with atomic result persistence
affects:
  - Phase 03 model-engine and clinical-result reader plans
tech_stack:
  added: []
  patterns: [Pydantic discriminated union, dependency-injected FastAPI service, deterministic Firestore paths]
key_files:
  created:
    - backend/app/clinical_rules.py
    - backend/app/prediction_service.py
    - backend/tests/test_prediction_routes.py
  modified:
    - backend/app/patients.py
    - backend/app/patient_routes.py
    - backend/tests/test_patients.py
decisions:
  - Current creatinine-rule status and future AKI prediction are separate Pydantic objects, storage collections, and response fields.
  - The production-safe engine persists an explicit unavailable forecast until Plan 03-05 supplies a verified engine behind the same protocol.
  - Result identity is canonical and deterministic from cohort, patient, cutoff, rule, outcome, and model/schema version inputs.
metrics:
  duration: 5m
  completed: 2026-10-04
  tasks_completed: 2
commits: 4
plan_head_before: 37669a20a3caa95280b07094c3a00b22b96255ce
plan_head_after: 3f9fe7eeeb015493d8f3d4e3813ba1e2e27b4b29
actuals:
  tokens: 7091
  tasks: 2
  commits: 4
status: complete
---

# Phase 03 Plan 01: Clinical Result Generation Summary

Doctor-authorized generation now calculates a traceable creatinine-only current-rule result and persists it beside an explicit unavailable 24-hour AKI forecast without conflating the two concepts.

## Completed Tasks

1. Added the protected clinical-result POST route, typed rule/forecast contracts, safe unavailable engine seam, active-cohort context resolution, and a single two-document persistence batch.
2. Added authorization, request-boundary, deterministic-identity, and injected-batch-failure coverage; fixed the nested patient ownership mapping exposed by those tests.

## Verification

- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_prediction_routes.py -q` — passed (4 tests).
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_patients.py backend/tests/test_auth.py backend/tests/test_health.py -q` — passed (26 tests).
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q` — passed (48 tests).
- `git diff --check 37669a2..3f9fe7e` — passed.

## Decisions Made

- Keep unavailable predictions first-class and omit probability and attributions entirely, rather than representing unavailability as zero risk.
- Use the same deterministic identifier under separate `clinical_rules` and `aki_predictions` subcollections so paired outputs share immutable context without sharing a result type.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 1 - Bug] Corrected clinical-context patient ownership mapping.
- **Found during:** Task 2 verification.
- **Issue:** Result persistence attempted to read `patient_id` directly from `PatientDetail` instead of its nested root patient.
- **Fix:** Derived the owned patient ID from `context.patient.patient.patient_id` for both result identity and persistence paths.
- **Files modified:** `backend/app/patients.py`
- **Commit:** `3f9fe7e`

2. [Rule 3 - Blocking issue] Restored the labeled Phase 3 plan position in planning state.
- **Found during:** Final state update.
- **Issue:** The pre-existing `STATE.md` position used narrative-only `Plan: Not started`, which the state SDK refuses to advance.
- **Fix:** Applied the SDK's disk-derived next position (`Current Plan: 2` of `6`) after this summary was created.
- **Files modified:** `.planning/STATE.md`

## TDD Gate Compliance

- RED: `d8b3e07` established the protected clinical-result route expectations before the tracer implementation.
- GREEN: `ebacfa6` implemented the tracer; `ec415bc` added safety-boundary cases; `3f9fe7e` resolved the resulting deterministic-persistence failure.
- REFACTOR: Not needed; the focused and full suites remained green after the minimal correction.

## Self-Check: PASSED

- Required implementation and test files exist.
- Task commits `d8b3e07`, `ebacfa6`, `ec415bc`, and `3f9fe7e` exist in git history.
