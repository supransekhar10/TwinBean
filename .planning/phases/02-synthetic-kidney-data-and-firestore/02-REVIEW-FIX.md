---
phase: 02-synthetic-kidney-data-and-firestore
fixed_at: 2026-10-03T21:40:10Z
review_path: C:/Users/pikun/OneDrive/Desktop/TwinBean/.planning/phases/02-synthetic-kidney-data-and-firestore/02-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-10-03T21:40:10Z  
**Source review:** `02-REVIEW.md`  
**Iteration:** 1

**Summary:**

- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: Reads do not enforce an active synthetic cohort

**Files modified:** `backend/app/patients.py`, `backend/tests/test_patients.py`, `backend/tests/test_patient_routes.py`  
**Commit:** `9df2e49`  
**Applied fix:** Reads now resolve and fully validate only `twinbean_metadata/active_cohort`, then scope every root and stream query to that immutable version.

### CR-02: Multi-batch seeding exposes a partially written cohort on failure

**Files modified:** `backend/app/patients.py`, `backend/tests/test_patients.py`  
**Commit:** `9df2e49`  
**Applied fix:** Seeding stages a new version, reads it back to verify counts, links, timestamps, provenance, and checksum, and switches the one active pointer only through a transaction after successful validation. Mid-batch, checksum, and activation-failure tests preserve the previous pointer.

### CR-03: Changed seed, generator version, or patient count mixes cohorts in the live namespace

**Files modified:** `backend/app/patients.py`, `backend/tests/test_patients.py`  
**Commit:** `9df2e49`  
**Applied fix:** A deterministic `cohort-{digest}` namespace contains all roots and both streams. Prior versions remain untouched and reads never mix versions.

### CR-04: Truthy coercion can relabel non-synthetic child records as synthetic

**Files modified:** `backend/app/patients.py`, `backend/tests/test_patients.py`  
**Commit:** `9df2e49`  
**Applied fix:** Stored records require literal `synthetic: true`, exact source labels, matching cohort/version/seed provenance, valid UTC timestamps, and typed identifiers; malformed strings such as `"false"` are rejected.

### CR-05: Detail reads do not verify child ownership before returning clinical history

**Files modified:** `backend/app/patients.py`, `backend/tests/test_patients.py`  
**Commit:** `9df2e49`  
**Applied fix:** Readback and detail parsing verify parent patient IDs, cohort provenance, and Firestore document path IDs for each EHR and IoT child while preserving separate streams.

### WR-01: Setup guide reports a live-verification state that is already superseded

**Files modified:** `docs/FIREBASE_SETUP.md`, `docs/SYNTHETIC_DATA.md`  
**Commit:** `86cdf02`  
**Applied fix:** Documentation now specifies every owned versioned path, write accounting (5,102 maximum writes), validation/activation behavior, and that the post-fix approved-runtime rerun is pending.

## Verification

- Python AST parsing passed for the modified Python modules and tests.
- Focused tests passed: `pytest tests/test_patients.py tests/test_patient_routes.py -q` (26 passed).
- Full backend tests passed: `pytest -q` (39 passed).
- Verification ran in the isolated review-fix worktree using the existing backend virtual environment; no credentials were accessed or printed.

---

_Fixed: 2026-10-03T21:40:10Z_  
_Fixer: the agent (gsd-code-fixer)_  
_Iteration: 1_
