---
phase: 02-synthetic-kidney-data-and-firestore
plan: "04"
subsystem: database
tags: [firebase-admin, cloud-firestore, fastapi, synthetic-data, authorization]
requires:
  - phase: 02-03
    provides: Doctor-authorized list/detail routes with separate EHR and IoT responses
provides:
  - Sanitized approved-runtime proof for Admin Firestore import and repeated deterministic seeding
  - Operations guide for backend-only Firestore setup, idempotent seed execution, and protected reads
  - Live confirmation that only exact-doctor FastAPI reads expose separately named EHR and IoT streams
affects: [phase-03-clinical-rules-and-aki-prediction, firestore-operations, authorization]
tech-stack:
  added: []
  patterns:
    - Backend-only explicit Firestore seed command with deterministic owned document IDs
    - Sanitized live-evidence records using checksums, bounded counts, and path shapes only
key-files:
  created:
    - .planning/phases/02-synthetic-kidney-data-and-firestore/02-04-LIVE-EVIDENCE.md
  modified:
    - docs/FIREBASE_SETUP.md
key-decisions:
  - "Approved-runtime proof records only non-sensitive runtime facts; credentials and bearer tokens remain excluded."
  - "Repeated seeding is validated through stable checksums, deterministic owned paths, and an unchanged unrelated canary."
  - "Protected patient reads remain FastAPI-only and require an exact role: doctor claim."
requirements-completed: [FIRE-01, FIRE-05, DATA-03]
actuals:
  tokens: 3182
  tasks: 2
  commits: 3
commits: 3
plan_head_before: 84994e66d5afa9fbce4fd2da853446aceac72e4f
plan_head_after: ad453e7a9c7c5b04e4fb02dc0fccda7bd5882cc5
duration: 13min
completed: 2026-10-03
status: complete
coverage:
  - id: D1
    description: "Backend-only Firestore setup, deterministic seed, and exact-doctor FastAPI read procedure."
    requirement: FIRE-01
    verification:
      - kind: other
        ref: "PowerShell documentation/source contract check"
        status: pass
      - kind: integration
        ref: "backend/.venv/Scripts/python.exe -m pytest backend/tests -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sanitized approved-runtime evidence for live Firestore import, repeated seed stability, unchanged canary, and protected reads."
    requirement: DATA-03
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/02-synthetic-kidney-data-and-firestore/02-04-LIVE-EVIDENCE.md"
        status: pass
      - kind: integration
        ref: "backend/.venv/Scripts/python.exe -m pytest backend/tests -q"
        status: pass
    human_judgment: false
---

# Phase 02 Plan 04: Firestore operations guide and approved-runtime proof Summary

**Backend-only Firestore operations are documented and live-approved evidence proves stable synthetic seeding, unchanged unrelated data, and exact-doctor FastAPI reads.**

## Performance

- **Duration:** 13min
- **Started:** 2026-10-03T09:22:27Z
- **Completed:** 2026-10-03T09:35:22Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- Documented Cloud Firestore enablement, backend-only credential boundaries, the exact deterministic seed command, and exact-doctor list/detail verification.
- Recorded approved-runtime evidence that the existing Admin SDK imports and repeated 12-patient seeds produce identical checksums and bounded owned paths.
- Proved an unrelated canary remained unchanged and protected FastAPI list/detail reads preserved separate EHR and IoT fields.

## Task Commits

1. **Task 1: Document Firestore enablement, deterministic seeding, and doctor-read verification** - `bc9de76` (docs)
2. **Task 2: Prove live Firestore seeding and protected reads in an approved runtime** - `3c2a396`, `ad453e7` (test, fix)

## Files Created/Modified

- `docs/FIREBASE_SETUP.md` - Safe operator procedure for Firestore setup, deterministic backend-only seeding, and FastAPI verification.
- `.planning/phases/02-synthetic-kidney-data-and-firestore/02-04-LIVE-EVIDENCE.md` - Sanitized approved-runtime import, seed, canary, readback, and authorization evidence.

## Decisions Made

- Recorded only non-sensitive runtime facts in live evidence; credentials, paths, tokens, keys, and user identifiers remain outside the repository.
- Used stable checksums, owned path shapes, and an unrelated canary hash to demonstrate idempotency without destructive collection operations.
- Retained FastAPI as the only patient-data boundary, requiring a refreshed token with exact `role: doctor`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed trailing Markdown whitespace from live evidence**
- **Found during:** Final Task 2 validation
- **Issue:** The three introductory evidence lines used hard-break whitespace, causing git diff --check to fail.
- **Fix:** Normalized the lines without changing any approved-runtime facts.
- **Files modified:** .planning/phases/02-synthetic-kidney-data-and-firestore/02-04-LIVE-EVIDENCE.md`n- **Verification:** git diff --check passes for the full plan range.
- **Committed in:** d453e7 (Task 2 correction)

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Formatting-only correction; live evidence content and scope are unchanged.

## Issues Encountered

- The restricted local sandbox redirected early seed attempts to `127.0.0.1:9`; approved external execution completed the required live verification without changing the implementation.
- The backend test suite emitted a pre-existing pytest cache permission warning but completed successfully with 40 passing tests.

## Known Stubs

None.

## Next Phase Readiness

Phase 2 now has an approved-runtime Firestore persistence and authorization record. Phase 3 can rely on backend-only Firestore operations and separate EHR/IoT evidence streams without adding SQLite or browser Firestore access.


## Self-Check: PASSED

- Found `docs/FIREBASE_SETUP.md`, `02-04-LIVE-EVIDENCE.md`, and this summary.
- Found task commits `bc9de76`, `3c2a396`, and `ad453e7`.
