---
phase: 02-synthetic-kidney-data-and-firestore
plan: "02"
subsystem: database
tags: [python, firestore, firebase-admin, synthetic-data, pytest]
requires:
  - phase: 02-01
    provides: Lazy Firebase Admin Firestore client and injected PatientRepository seam.
provides:
  - Deterministic adult CKD and independent simulated IoT cohort generator.
  - Validated owned-path Firestore seed manifest with bounded set-only batches.
  - Explicit backend seed CLI with deterministic non-sensitive reporting.
affects: [02-03-patient-detail, 02-04-operations, clinical-rules, prediction]
tech-stack:
  added: []
  patterns: [Pure versioned generators, deterministic Firestore manifests, validate-before-write seed commands]
key-files:
  created:
    - backend/app/synthetic_data.py
    - backend/scripts/seed_synthetic_data.py
  modified:
    - backend/app/patients.py
    - backend/tests/test_synthetic_data.py
    - backend/tests/test_patients.py
key-decisions:
  - "Seed manifests validate all synthetic provenance, stable IDs, parent relationships, and document sizes before opening a Firestore batch."
  - "The seed path uses deterministic document IDs and batch.set only; no collection-wide cleanup or generated document IDs are available."
patterns-established:
  - "Separate EHR and IoT streams in models, Firestore subcollections, and persisted payloads."
  - "Expose privileged data mutation only through explicit backend argparse commands."
requirements-completed: [FIRE-01, DATA-01, DATA-02, DATA-03]
actuals:
  tokens: 8713
  tasks: 2
  commits: 4
commits: 4
plan_head_before: 7136b87eb9913903e64cc00b1b1afa2e7e7ea547
plan_head_after: 00c0b4c3ca449f45ec0908b3bd17ee6fd398fb7a
coverage:
  - id: D1
    description: Reproducible adult CKD histories with explicit synthetic provenance and stable IDs.
    requirement: DATA-01
    verification:
      - kind: unit
        ref: backend/tests/test_synthetic_data.py
        status: pass
    human_judgment: false
  - id: D2
    description: Independently typed and persisted simulated IoT observations.
    requirement: DATA-02
    verification:
      - kind: unit
        ref: backend/tests/test_synthetic_data.py and backend/tests/test_patients.py
        status: pass
    human_judgment: false
  - id: D3
    description: Validated deterministic Firestore manifest and explicit seed command.
    requirement: FIRE-01
    verification:
      - kind: unit
        ref: backend/tests/test_patients.py
        status: pass
    human_judgment: false
  - id: D4
    description: Firestore-only owned persistence for Phase 2 patient, EHR, and IoT records.
    requirement: DATA-03
    verification:
      - kind: unit
        ref: backend/tests/test_patients.py
        status: pass
    human_judgment: false
duration: 26min
completed: 2026-10-03
status: complete
---

# Phase 02 Plan 02: Deterministic synthetic cohort and idempotent Firestore seed Summary

**Versioned synthetic adult CKD histories and independent simulated IoT records now seed Firestore through validated deterministic paths and bounded set-only batches.**

## Performance

- **Duration:** 26 min
- **Started:** 2026-10-03T08:01:30Z
- **Completed:** 2026-10-03T08:27:56Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- Added a pure, typed, reproducible adult CKD cohort generator with stable patient/EHR/IoT identifiers and UTC synthetic provenance.
- Added a prevalidated Firestore manifest writer that uses only `batch.set()` and `batch.commit()` on deterministic patient, EHR, and IoT paths.
- Added an explicit argparse seed command that prints counts, generator version, seed, and manifest checksum without loading on API startup.

## Task Commits

1. **Task 1 RED: Define deterministic synthetic cohort contract** - `71724b5` (test)
2. **Task 1 GREEN: Generate deterministic synthetic CKD cohorts** - `1fcd9d4` (feat)
3. **Task 2 RED: Define Firestore seed manifest contract** - `876a785` (test)
4. **Task 2 GREEN: Add deterministic Firestore cohort seeding** - `00c0b4c` (feat)

## Files Created/Modified

- `backend/app/synthetic_data.py` - Pure deterministic typed generator for adult CKD EHR and simulated IoT records.
- `backend/app/patients.py` - Owned-path manifest validation, bounded batch writer, and `SeedResult`.
- `backend/scripts/seed_synthetic_data.py` - Explicit backend-only seeding command.
- `backend/tests/test_synthetic_data.py` - Determinism, provenance, adult CKD, and source-separation contract coverage.
- `backend/tests/test_patients.py` - Fake Firestore path, batching, idempotency, safety, and CLI contract coverage.

## Decisions Made

- Validate the complete cohort manifest before the first Firestore batch is opened, preventing invalid provenance, parent paths, or over-limit payloads from producing partial writes.
- Keep roots lean and put EHR and IoT records in their own named subcollections to preserve source separation for future consumers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected a manifest-validator type annotation before test execution.**
- **Found during:** Task 2
- **Issue:** The first implementation had a mismatched bracket in the validator annotation.
- **Fix:** Rebuilt the temporary replacement with the corrected annotation before replacing the production file.
- **Files modified:** `backend/app/patients.py`
- **Verification:** `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_patients.py -q` and full backend tests pass.
- **Committed in:** `00c0b4c`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** The correction was limited to an implementation annotation; no scope or behavior changed.

## Verification

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_synthetic_data.py backend/tests/test_patients.py backend/tests -q` - 14 passed.
- `git diff --check` - passed.
- Fake-client contracts confirm only deterministic `set()` and `commit()` operations are used.

## Known Stubs

None.

## Issues Encountered

None after the inline annotation correction.

## User Setup Required

None - the seed command uses the existing backend Firestore factory when an operator explicitly invokes it.

## Next Phase Readiness

Patient roots and separated EHR/IoT subcollections are ready for the Phase 02 read-detail and operational verification plans. No live Firestore mutation was attempted in this offline contract plan.

## Self-Check: PASSED

- All five planned implementation and test files exist.
- All four task commits are present in Git history.

---
*Phase: 02-synthetic-kidney-data-and-firestore*
*Completed: 2026-10-03*
