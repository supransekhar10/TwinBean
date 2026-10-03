# Phase 02 approved-runtime live evidence

**Status:** Passed in an organization-approved runtime  
**Verification time (UTC):** 2026-10-03T09:31:13.1890311Z  
**Target Firebase project:** `twinbean-a7011`  
**Operator approval:** `approved-runtime verification passed`

## Sanitization boundary

This record contains only non-sensitive runtime facts. It intentionally excludes
tokens, passwords, user identifiers, email addresses, API keys, service-account
paths and contents, private keys, and credential values. Backend configuration
matched the target project and a backend-only credential was present; no
credential location or material is recorded here.

## Approved runtime and Admin import

- Runtime: Microsoft Windows NT 10.0.26300.0; PowerShell 5.1.26100.9444; Python
  3.12.10.
- Existing Firebase Admin Firestore dependency import succeeded with:
  `Admin Firestore import OK`.
- This proves the existing Admin SDK was used in the approved runtime; no SDK was
  substituted and no Application Control setting was changed.

## Deterministic seed proof

The backend-only seed was run explicitly from `backend` with the exact bounded
configuration:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_synthetic_data --seed 2402 --generator-version phase2-v1 --time-basis 2026-01-01T00:00:00+00:00 --patient-count 12
```

Multiple repeated approved-network runs returned the same manifest checksum:

`c9d20dab48fb29ed67f48a57b0a7fdce4d0bb433ea82595c1cf163ae9cda14db`

Each run reported the same bounded result:

| Record type | Count |
| --- | ---: |
| Patients | 12 |
| EHR events | 312 |
| IoT observations | 288 |
| Total writes | 612 |
| Maximum writes per batch | 100 |
| Configured total-write safety ceiling | 10,100 |

The implementation used `set()`-only batches. It did not delete or reset any
collection. Its only owned target shapes were:

- `patients/{patient_id}`
- `patients/{patient_id}/ehr_events/{event_id}`
- `patients/{patient_id}/iot_observations/{observation_id}`

Representative stable synthetic owned paths observed during verification:

- `patients/tbp-b63219025d655434b7e5ecb5f19d2240`
- `patients/tbp-b63219025d655434b7e5ecb5f19d2240/ehr_events/ehr-0ecce74a38575654802e6bcf64ede92c`
- `patients/tbp-b63219025d655434b7e5ecb5f19d2240/iot_observations/iot-7754005149fa56eb8cd5a881bc394711`

## Unrelated-data canary

The verification canary outside the owned `patients` hierarchy was
`twinbean_verification/phase2_canary`. Its non-sensitive payload SHA-256 was
`228594a1524620da5246041cfdcb31fb63ee20be298a661a038f0a03837a1b49` before
and after two repeated seeds. The unchanged hash proves the seed did not mutate
that unrelated document.

## Persisted readback

Readback of the deterministic expected cohort found 12 patient roots, 312 EHR
events, and 288 IoT observations. Every child record matched its parent patient
ID. Timestamps were UTC and ordered within their respective streams.

- EHR UTC range: `2025-07-05T00:00:00+00:00` through
  `2025-12-02T00:00:00+00:00`.
- IoT UTC range: `2025-11-06T00:00:00+00:00` through
  `2025-12-25T00:00:00+00:00`.

## Doctor-authorized FastAPI reads

A trusted existing doctor-claim user refreshed its Firebase ID token after
claim assignment. The short-lived token was held only in memory and sent only
to FastAPI; it is not recorded in this file.

- `GET /patients` returned HTTP 200 with 12 synthetic patients.
- `GET /patients/{patient_id}` returned HTTP 200 for a returned patient ID and
  preserved separate `ehr_history` and `iot_observations` fields with 26 and 24
  records respectively.
- Existing automated authorization evidence covers the required HTTP 403 result
  for a verified non-doctor; no additional account was created for live proof.

These results confirm the exact `role: doctor` boundary and that EHR history and
simulated IoT observations remain separate evidence streams through the
protected FastAPI API.

## Result

The approved-runtime checkpoint is complete: the existing Admin Firestore SDK
imported successfully, identical seeds were stable and bounded to TwinBean-owned
paths, the unrelated canary was unchanged, and exact-doctor list/detail reads
succeeded through FastAPI without exposing sensitive credentials or tokens.
