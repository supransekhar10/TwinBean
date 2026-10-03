---
phase: 02-synthetic-kidney-data-and-firestore
plan: "03"
subsystem: api
tags: [fastapi, firestore, firebase-admin, pytest, synthetic-data]
requires:
  - phase: 02-01
    provides: Doctor-authorized patient list and repository dependency seam
  - phase: 02-02
    provides: Synthetic patient, EHR event, and IoT observation persistence models
provides:
  - Doctor-only patient detail endpoint with separately serialized EHR and IoT histories
  - Bounded Firestore subcollection reads with explicit missing-patient behavior
  - Offline regression coverage for authorization, absence, empty streams, and ordering
affects: [phase-05-patient-detail-presentation, patient-api]
tech-stack:
  added: []
  patterns:
    - Typed Firestore snapshot conversion stays inside PatientRepository.
    - Patient evidence streams remain independently queried, bounded, ordered, and serialized.
key-files:
  created: []
  modified:
    - backend/app/patients.py
    - backend/app/patient_routes.py
    - backend/tests/test_patients.py
    - backend/tests/test_patient_routes.py
key-decisions:
  - "Expose the public detail contract as patient, ehr_history, and iot_observations without a combined history field."
  - "Use direct require_doctor dependencies on both list and detail routes, with a typed 404 only for the domain-level missing result."
  - "Normalize each history by its own UTC timestamp after the independent bounded Firestore query."
requirements-completed: [FIRE-05, DATA-02, DATA-03]
actuals:
  tokens: 8255
  tasks: 2
  commits: 4
commits: 4
plan_head_before: 3b4460faf2ec145184ee19def0df68e372af41fe
plan_head_after: 5032dc49115259d71a885a5065badf912ae97160
duration: 7min
completed: 2026-10-03
status: complete
coverage:
  - id: D1
    description: Doctor-authorized patient detail preserves separate typed EHR and simulated IoT histories.
    requirement: FIRE-05
    verification:
      - kind: unit
        ref: backend/tests/test_patients.py::test_repository_reads_distinct_bounded_ehr_and_iot_histories_without_snapshots
        status: pass
      - kind: integration
        ref: backend/tests/test_patient_routes.py::test_doctor_can_read_separate_typed_patient_detail
        status: pass
    human_judgment: false
  - id: D2
    description: Patient detail short-circuits missing roots, keeps empty streams, and independently normalizes timestamps.
    requirement: DATA-02
    verification:
      - kind: unit
        ref: backend/tests/test_patients.py::test_missing_patient_root_skips_all_child_stream_queries
        status: pass
      - kind: unit
        ref: backend/tests/test_patients.py::test_repository_normalizes_each_stream_to_ascending_utc_timestamp_order
        status: pass
      - kind: integration
        ref: backend/tests/test_patient_routes.py::test_missing_detail_root_returns_404_without_storage_detail
        status: pass
    human_judgment: false
---

# Phase 02 Plan 03: Separate doctor-authorized patient detail streams Summary

**Doctor-protected FastAPI detail reads now return a synthetic patient root with independently queried, bounded, and timestamp-ordered EHR and simulated IoT histories.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-03T14:37:53+05:30
- **Completed:** 2026-10-03T14:44:32+05:30
- **Tasks:** 2/2
- **Files modified:** 4
- **Tests:** 40 passed via `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q`

## Accomplishments

- Added `PatientDetail` and `PatientRepository.get_patient()` with a direct root read plus separate `ehr_events` and `iot_observations` queries, each capped at 500 records.
- Added `GET /patients/{patient_id}` with direct `Depends(require_doctor)`, strict stable-ID validation, and a typed 404 for an absent root.
- Converted snapshots into domain models inside the repository and independently normalized both histories by their own UTC timestamp field.
- Added offline tests proving authorization happens before repository access, roots short-circuit child queries, empty streams stay distinct, and responses never expose Firestore snapshots.

## Task Commits

1. **Task 1: Read and return EHR and IoT histories as separate detail fields**
   - `5208580` test: define separate patient detail reads
   - `3862b88` feat: add separate patient detail reads
2. **Task 2: Define missing-patient, empty-stream, and regression behavior**
   - `79579d1` test: define detail absence and ordering behavior
   - `5032dc4` feat: normalize patient detail histories

## Files Created/Modified

- `backend/app/patients.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â typed patient detail contract, safe root lookup, independent bounded child reads, and timestamp normalization.
- `backend/app/patient_routes.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â doctor-only detail route with stable identifier validation and 404 translation.
- `backend/tests/test_patients.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â repository contracts for stream separation, bounds, safe absence, empty values, and ordering.
- `backend/tests/test_patient_routes.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â detail authorization, serialization shape, identifier validation, and 404 contracts.

## Decisions Made

- The response contract remains exactly `patient`, `ehr_history`, and `iot_observations`; no combined history field is introduced.
- Missing root documents map to `None` in the repository, avoiding child reads; only the route maps that domain result to HTTP 404.
- Query ordering is reinforced with independent in-memory UTC normalization so fake and Firestore-like responses are deterministic.

## TDD Gate Compliance

- RED evidence for detail reads: `RED_EVIDENCE_OK` for `test_repository_reads_distinct_bounded_ehr_and_iot_histories_without_snapshots`.
- RED evidence for ordering: `RED_EVIDENCE_OK` for `test_repository_normalizes_each_stream_to_ascending_utc_timestamp_order`.
- Both RED commits precede their corresponding GREEN commits.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pytest reports a non-blocking cache-permission warning for the pre-existing `backend/.pytest_cache` path; the full backend suite completed successfully and no generated files were staged.

## User Setup Required

None - the repository and route tests remain offline and do not require live Firestore credentials.

## Next Phase Readiness

Phase 04 can document and manually verify the backend-only Firestore seed/read workflow using the stable doctor-authorized detail contract.

## Self-Check: PASSED

- Confirmed all four plan-owned source/test files and this summary exist.
- Confirmed task commits `5208580`, `3862b88`, `79579d1`, and `5032dc4` exist in git history.
