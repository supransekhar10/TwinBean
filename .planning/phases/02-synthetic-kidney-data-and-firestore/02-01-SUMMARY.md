---
phase: 02-synthetic-kidney-data-and-firestore
plan: "01"
subsystem: api
tags: [fastapi, firebase-admin, firestore, authorization, pytest]
requires:
  - phase: 01-secure-backend-foundation
    provides: FastAPI health routes, Firebase token verification, and exact doctor-role guard
provides:
  - Doctor-authorized bounded patient root-summary endpoint
  - Lazy Firebase Admin Firestore client and injectable repository seam
affects: [patient-detail-api, synthetic-data-seeding, doctor-dashboard]
tech-stack:
  added: []
  patterns:
    - Function-local Firestore Admin import for offline route-test compatibility
    - FastAPI dependency override seam for server-only patient repositories
key-files:
  created:
    - backend/app/firestore.py
    - backend/app/patients.py
    - backend/app/patient_routes.py
    - backend/tests/test_patient_routes.py
  modified:
    - backend/app/main.py
key-decisions:
  - "Patient lists return only typed root summary fields; longitudinal EHR and IoT records remain outside the list response."
  - "The existing require_doctor dependency precedes repository access for every patient-list request."
  - "Firestore imports stay function-local so offline FastAPI tests never load the blocked cygrpc extension."
patterns-established:
  - "Patient repositories construct deterministic Firestore queries and serialize snapshots into explicit response models."
  - "Protected routes expose an overridable repository dependency while retaining the shared auth dependency unchanged."
requirements-completed: [FIRE-01, FIRE-05]
coverage:
  - id: D1
    description: Doctor-only bounded patient root-summary list through the lazy Firestore repository seam.
    requirement: FIRE-01
    verification:
      - kind: integration
        ref: backend/tests/test_patient_routes.py#test_doctor_can_list_typed_root_patient_summaries
        status: pass
      - kind: unit
        ref: backend/tests/test_patient_routes.py#test_repository_lists_only_bounded_ordered_root_summaries
        status: pass
    human_judgment: false
  - id: D2
    description: Patient-list authorization rejects missing, invalid, and non-doctor tokens before repository access.
    requirement: FIRE-05
    verification:
      - kind: integration
        ref: backend/tests/test_patient_routes.py#test_missing_token_is_unauthorized_without_repository_access
        status: pass
      - kind: integration
        ref: backend/tests/test_patient_routes.py#test_invalid_token_is_unauthorized_without_repository_access
        status: pass
      - kind: integration
        ref: backend/tests/test_patient_routes.py#test_non_doctor_is_forbidden_without_repository_access
        status: pass
    human_judgment: false
actuals:
  tokens: 2493
  tasks: 2
  commits: 3
plan_head_before: a1a07f0d4b1e267f3bec5d4d2536ac3deba490df
plan_head_after: e11ec1d582831950d37dea851c6942b39b284914
duration: 28min
completed: 2026-10-03
status: complete
---

# Phase 02 Plan 01: Doctor-authorized Firestore list tracer Summary

**A doctor-only FastAPI patient list now crosses an injectable repository seam into a lazily loaded Firebase Admin Firestore client while returning bounded typed root summaries only.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-10-03T07:32:37Z
- **Completed:** 2026-10-03T08:00:37Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- Added a function-local Firebase Admin Firestore client factory that reuses the existing Admin app initializer.
- Added `GET /patients`, guarded by unchanged exact `require_doctor` authorization and bounded to 1..100 results.
- Added offline tests for query shape, root-summary-only serialization, 401/403 repository non-invocation, empty results, and Phase 1 health regressions.

## Task Commits

1. **Task 1 RED: failing patient-list route contract** - `4d6248c` (test)
2. **Task 1 GREEN: doctor-authorized patient list tracer** - `1605449` (feat)
3. **Task 2: authorization and bounds edge coverage** - `e11ec1d` (test)

## Files Created/Modified

- `backend/app/firestore.py` - Lazy backend-only Firebase Admin Firestore client factory.
- `backend/app/patients.py` - Typed patient root summary and deterministic bounded repository query.
- `backend/app/patient_routes.py` - Doctor-protected list router and overridable repository dependency.
- `backend/app/main.py` - Additive patient-router registration.
- `backend/tests/test_patient_routes.py` - Offline tracer, authorization, bounds, and serialization tests.

## Decisions Made

- Patient list responses serialize only `patient_id`, `display_name`, `age`, and `ckd_stage`; event arrays cannot cross the API seam.
- Route authorization remains the existing `require_doctor` dependency, so denied requests never reach `list_patients`.
- The Firestore SDK import occurs only inside the client factory to preserve local test importability under the `cygrpc` policy block.

## TDD Evidence

- **RED:** `GET /patients` intentionally failed with `404` before route implementation.
- **GREEN:** `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q` passed with 15 tests.
- **REFACTOR:** No separate refactor was needed; the minimal repository and route seam remained clear after the edge-case tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the repository test to assert typed summary serialization.**
- **Found during:** Task 1 focused GREEN verification.
- **Issue:** The query-shape test compared `PatientSummary` instances directly to dictionaries.
- **Fix:** Serialized each typed result with `model_dump()` before asserting the safe root-summary fields.
- **Files modified:** `backend/tests/test_patient_routes.py`
- **Verification:** Focused and full backend test suites pass.
- **Committed in:** `1605449`

**Total deviations:** 1 auto-fixed (Rule 1).

## Issues Encountered

- The local patch helper could not update pre-existing files, so narrowly verified replacements were used for the planned router registration and test expansion. No behavior or scope changed.

## User Setup Required

None - no external service configuration was required for offline verification.

## Next Phase Readiness

- Subsequent Phase 2 work can seed deterministic root documents and add separate EHR/IoT subcollections behind the established repository seam.
- The approved-runtime live Firestore check remains intentionally deferred to Plan 02-04.

## Self-Check: PASSED

---

*Phase: 02-synthetic-kidney-data-and-firestore*
*Completed: 2026-10-03*
