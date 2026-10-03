---
phase: 02-synthetic-kidney-data-and-firestore
reviewed: 2026-10-03T21:34:41Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - backend/app/patients.py
  - backend/app/synthetic_data.py
  - backend/app/patient_routes.py
  - backend/scripts/seed_synthetic_data.py
  - backend/tests/test_patients.py
  - backend/tests/test_patient_routes.py
  - docs/FIREBASE_SETUP.md
  - docs/SYNTHETIC_DATA.md
findings:
  critical: 5
  warning: 1
  info: 0
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-10-03T21:34:41Z
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found

## Summary

The generator itself is deterministic and the route dependency enforces the doctor role before repository access. However, the persistence and read paths treat the global `patients` collection as the live cohort. A seed larger than one Firestore batch is committed directly there, and reads neither select an active immutable cohort nor validate synthetic provenance and ownership. This can expose partial, stale, mixed, or incorrectly labelled patient records to clinicians.

The targeted test suite passes (27 tests), but it only exercises successful batches and well-formed synthetic fixtures; it does not cover activation failure, multiple cohorts, or malformed Firestore records.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Reads do not enforce an active synthetic cohort

**Classification:** BLOCKER

**File:** `backend/app/patients.py:68-76`, `backend/app/patients.py:83-114`

**Issue:** `list_patients` streams every root in the global `patients` collection, and `get_patient` returns any document at the requested deterministic-looking path plus all of its child documents. Neither method checks an active cohort/version, exact synthetic provenance, or a manifest checksum. A doctor can therefore receive records from an abandoned/failed import or any non-synthetic record that reaches that collection, violating the synthetic-only data boundary.

**Fix:** Store each seed under an immutable cohort-version namespace and keep one small active-cohort metadata document. Resolve that document first on every list/detail read, scope queries and document paths to its version, and reject a cohort whose stored provenance, counts, links, or checksum do not validate.

### CR-02: Multi-batch seeding exposes a partially written cohort on failure

**Classification:** BLOCKER

**File:** `backend/app/patients.py:116-124`

**Issue:** The complete manifest is prevalidated, but `_batch_chunks` can split it into 100-write batches and each batch is committed immediately. A normal 12-patient seed contains hundreds of documents, so a failure after an earlier `batch.commit()` leaves roots and/or streams visible to the route above. There is no post-write verification or atomic publication step, and a previous valid cohort is not protected from this partial state.

**Fix:** Write all documents only to a new inactive immutable cohort version. Read that version back and validate expected counts, each child-to-parent link, and the manifest checksum. Only then transactionally switch the active-cohort pointer; if any write or validation fails, do not switch it and leave the previous active pointer unchanged.

### CR-03: Changed seed, generator version, or patient count mixes cohorts in the live namespace

**Classification:** BLOCKER

**File:** `backend/app/patients.py:185-198`, `backend/app/synthetic_data.py:229-230`

**Issue:** Patient and child paths are all written below `patients/{id}` and contain no cohort-version identifier. IDs change when the seed or generator version changes, so a later successful seed adds another cohort that `list_patients` returns alongside the old one. Reducing `patient_count` with otherwise identical inputs also leaves higher-index roots from the previous run. The API has no way to identify which complete cohort is intended to be live.

**Fix:** Introduce a cohort ID derived from the complete generation configuration/manifest and write all roots and streams below that version. Activate exactly one validated version through metadata rather than treating the global `patients` collection as the active data set. Do not delete the prior version during activation.

### CR-04: Truthy coercion can relabel non-synthetic child records as synthetic

**Classification:** BLOCKER

**File:** `backend/app/patients.py:147-159`, `backend/app/patients.py:162-174`

**Issue:** The deserializers use `bool(data["synthetic"])`. In Python, a stored string such as `"false"` is truthy, so a malformed or nonconforming Firestore child is returned through the protected API with `synthetic: true`. The read path also accepts arbitrary source strings and does not compare the child version/seed to the selected parent/cohort.

**Fix:** Parse Firestore documents with strict input models (or explicitly require `data["synthetic"] is True`) and require exact allowed source labels, correct field types, and matching cohort/version/seed. Reject invalid records/cohorts rather than coercing them into apparently trustworthy clinical evidence.

### CR-05: Detail reads do not verify child ownership before returning clinical history

**Classification:** BLOCKER

**File:** `backend/app/patients.py:90-114`, `backend/app/patients.py:147-174`

**Issue:** The EHR and IoT deserializers retain each document's stored `patient_id`, but `get_patient` never compares it to the requested root ID (nor validates that both streams have the active cohort's provenance). A wrongly linked child document in a subcollection is returned as part of another patient's detail response, creating a false clinical history even though its stored ID says it belongs elsewhere.

**Fix:** During cohort validation, verify every child path, `patient_id`, provenance/version, and checksum against the staged parent. At read time serve only a previously validated active version; defensively reject any child whose `patient_id` or provenance does not match its root and active cohort.

## Warnings

### WR-01: Setup guide reports a live-verification state that is already superseded

**Classification:** WARNING

**File:** `docs/FIREBASE_SETUP.md:67-71`

**Issue:** The setup guide says approved-runtime Firestore import, persistence, and doctor reads are pending and instructs operators to move to another runtime. The phase's live-evidence record reports that this verification has completed. The contradiction can cause operators to repeat or avoid the wrong verification procedure.

**Fix:** Replace the pending-host language with a concise pointer to the approved-runtime evidence and retain only current, reproducible verification prerequisites and commands.

---

_Reviewed: 2026-10-03T21:34:41Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
