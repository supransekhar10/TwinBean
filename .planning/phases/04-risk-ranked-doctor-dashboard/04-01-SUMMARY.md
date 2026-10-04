---
phase: 04-risk-ranked-doctor-dashboard
plan: "01"
subsystem: backend
tags: [fastapi, firestore, authorization, dashboard]
requires: [03-clinical-rules-and-aki-prediction]
provides: [doctor-protected-dashboard-projection]
affects: [04-02]
tech-stack:
  added: []
  patterns: [discriminated-unavailable-risk, server-owned-ranking]
key-files:
  created: [backend/tests/test_dashboard_routes.py]
  modified: [backend/app/patients.py, backend/app/patient_routes.py]
decisions:
  - Missing stored predictions use an unavailable union member with no probability field.
  - Dashboard ordering is owned by the backend and uses display name plus patient ID as stable tie-breakers.
status: complete
completed: 2026-10-05
---

# Phase 4 Plan 01: Dashboard Backend Summary

Doctor-protected bounded dashboard projection with server-side risk ranking and explicitly separate current-rule and future-prediction summaries.

## Tasks Completed

- Added dashboard DTOs and a bounded repository projection over latest stored clinical evidence.
- Added `GET /dashboard/patients` behind the existing exact `role: doctor` dependency.
- Preserved unavailable risk without a probability and avoided prediction-generation side effects.

## TDD Gate Compliance

- RED: `29f0bd9` added behavior tests that failed on the missing repository method and route.
- GREEN: `e7e962a` implemented the projection and protected endpoint.
- REFACTOR: No separate refactor was required after the minimal implementation passed.

## Verification

- Focused dashboard and auth tests: 10 passed.
- Complete backend suite: 104 passed.

## Deviations from Plan

None - plan executed as written.

## Self-Check: PASSED

All owned source and test files exist, both commits are present, and focused plus complete backend verification passed.
