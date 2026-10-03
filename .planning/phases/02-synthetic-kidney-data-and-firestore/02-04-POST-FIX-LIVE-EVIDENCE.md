# Phase 02 versioned-cohort live evidence

**Status:** Passed
**Verification time (UTC):** 2026-10-03T21:49:39.2148256Z
**Target Firebase project:** `twinbean-a7011`
**Runtime:** Windows NT 10.0.26300.0; PowerShell 5.1.26100.9444; Python 3.12.10

## Sanitization boundary

This record excludes credentials, paths to credentials, tokens, passwords, API keys, private keys, email addresses, and user identifiers. The configured Firebase project and backend service-account project matched before any write, and the Firebase Admin Firestore import succeeded.

## Approved write contract

The exact backend-only command was run twice:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_synthetic_data --seed 2402 --generator-version phase2-v1 --time-basis 2026-01-01T00:00:00+00:00 --patient-count 12
```

Preflight confirmed these TwinBean-owned paths:

- `twinbean_cohorts/{cohort_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/ehr_events/{event_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/iot_observations/{observation_id}`
- `twinbean_metadata/active_cohort`

The 12-patient run was bounded to 614 writes: 612 clinical documents, one cohort descriptor, and one atomic active-pointer write. The configured ceiling is 5,102 writes at 100 patients; staged batches are capped at 100 writes. No delete or reset operation was used.

## Repeat-seed and activation result

Both runs completed with identical results:

| Item | Actual result |
|------|---------------|
| Active cohort | `cohort-6e5aca83ddf6e3fb2e4c3a24` |
| Manifest checksum | `2532df28923f3ebe1ac2e5de11ec18746f4e7ada5015d32a140ba25ffe45bb53` |
| Patients | 12 |
| EHR events | 312 |
| IoT observations | 288 |

The second run produced the same immutable cohort ID and checksum. The active pointer referenced that validated version only after staged readback passed.

## Independent readback

Readback confirmed:

- All 12 patient root IDs matched their document IDs.
- All 312 EHR and 288 IoT child records matched their parent patient and active cohort.
- Exact synthetic source labels and literal boolean provenance were present.
- A representative detail contained 26 EHR events and 24 IoT observations in separate streams.
- EHR UTC range: `2025-07-05T00:00:00+00:00` to `2025-12-02T00:00:00+00:00`.
- IoT UTC range: `2025-11-06T00:00:00+00:00` to `2025-12-25T00:00:00+00:00`.

The unrelated canary at `twinbean_verification/phase2_canary` retained SHA-256 `228594a1524620da5246041cfdcb31fb63ee20be298a661a038f0a03837a1b49`, identical to the pre-fix evidence.

## Protected API verification

A short-lived Firebase ID token for an existing trusted doctor-claim account was created and held only in memory.

- `GET /patients`: HTTP 200 with 12 synthetic patients.
- `GET /patients/{patient_id}`: HTTP 200 with 26 EHR events and 24 IoT observations in separate response fields.
- Exact `role: doctor` was verified by the backend.
- Automated negative tests cover missing/invalid token rejection and verified non-doctor HTTP 403 without repository access.

## Result

The post-fix versioned-cohort contract passed: deterministic staging, strict readback validation, atomic activation, separate aligned streams, unrelated-data preservation, and doctor-authorized reads were all observed without exposing credentials.
