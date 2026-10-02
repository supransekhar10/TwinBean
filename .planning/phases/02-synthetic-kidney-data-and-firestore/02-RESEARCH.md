---
phase: "2"
status: complete
researched: "2026-10-03"
confidence: medium
---

# Phase 2: Synthetic Kidney Data and Firestore - Research

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Synthetic Cohort Contract
- **D-01:** Use a versioned deterministic generator with a fixed configurable seed and stable synthetic patient IDs so the same inputs reproduce the same cohort.
- **D-02:** Generate adult-only CKD histories with plausible demographics, CKD context, encounters, medications, and longitudinal kidney-relevant laboratory observations.
- **D-03:** Mark generated records explicitly as synthetic and record generator version, seed, and UTC timestamps as provenance. Never derive fixtures from real patient data.

### EHR and IoT Separation
- **D-04:** Store patient identity and cohort summary separately from longitudinal observations.
- **D-05:** Keep EHR events and simulated IoT observations in distinct typed Firestore subcollections with independent event timestamps and source metadata. -- **Reversibility:** costly -- combining these streams later would require a Firestore migration and changes to consumers.
- **D-06:** IoT observations should cover kidney-relevant home monitoring such as weight, blood pressure, and heart rate, while EHR records remain the source for clinical history and laboratory data.

### Firestore Seeding and Provenance
- **D-07:** Provide an explicit backend-only seed command; do not seed implicitly during API startup.
- **D-08:** Make seeding idempotent for the same generator version and seed. Update only deterministic TwinBean-owned documents and never delete or overwrite unrelated Firestore data.
- **D-09:** Cloud Firestore is the authoritative data store. Do not add SQLite or a browser-side persistence path.

### Doctor-Only Read Surface
- **D-10:** Browser code must obtain patient data through FastAPI; it must not query Firestore directly.
- **D-11:** Expose protected patient-list and patient-detail data endpoints using the existing `require_doctor` dependency for exact `role: doctor` authorization.
- **D-12:** Return EHR history and IoT observations as separately named response fields so future interfaces cannot accidentally present them as one source.

### the agent's Discretion
- Choose the small prototype cohort size, observation cadence, exact field constraints, endpoint pagination threshold, and internal Python module layout, provided records remain clinically plausible, deterministic, and sufficient for later model evaluation.

### Deferred Ideas (OUT OF SCOPE)
- Clinical rules, AKI prediction, prediction availability, and SHAP explanations belong to Phase 3.
- Dashboard ordering and patient-detail presentation belong to Phases 4 and 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIRE-01 | Backend accesses Cloud Firestore through the Firebase Admin SDK. | Reuse the Admin app in a backend-only Firestore repository. |
| FIRE-05 | Patient data access is limited to authenticated users authorized as doctors. | Apply the existing doctor dependency to list and detail routes. |
| DATA-01 | System generates or loads synthetic histories for adult patients with chronic kidney disease. | Use a pure deterministic versioned generator. |
| DATA-02 | System produces a simulated IoT stream independently from patient history data. | Generate and persist a separately typed stream/subcollection. |
| DATA-03 | System stores prototype patient, observation, rule, and prediction data in Cloud Firestore rather than SQLite. | Persist the Phase-2 patient/EHR/IoT subset in Firestore; defer rules/predictions. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Use only synthetic patient and simulated IoT data; never handle real PHI.
- Retain server-side ID-token verification and exact `role: doctor` authorization for every protected endpoint.
- Keep Firebase service-account credentials backend-only and out of Git/browser configuration.
- Use Cloud Firestore only; do not introduce SQLite, browser-side persistence, clinical rules, predictions, or the full dashboard/ML pipeline.
- Follow implement → check → fix; after three failed checks, stop with evidence rather than weakening tests.

## Summary

Use the existing Firebase Admin Python dependency and create a Firestore client from the already initialized Admin app. Firebase’s official Python quickstart uses Admin initialization followed by `firestore.client()`. [CITED: https://firebase.google.com/docs/firestore/quickstart-server] The current foundation already initializes the process app and its doctor guard rejects every claim except the exact value `doctor`. [VERIFIED: backend/app/firebase.py:7-18] `return firebase_admin.get_app()` and `return firebase_admin.initialize_app(credentials.ApplicationDefault(), options)`; [VERIFIED: backend/app/auth.py:35-41] `if claims.get("role") != "doctor":`.

Model each patient as a small root summary plus two independently queried event subcollections. Firestore recommends lightweight documents and subcollections for expanding data; identical subcollection IDs also permit later collection-group queries. [CITED: https://firebase.google.com/docs/firestore/data-model] Keep generator creation pure, use explicit deterministic document IDs, and write only its manifest through an explicit backend-only seed command.

**Primary recommendation:** use a pure generator + repository + explicit `seed_synthetic_data` command; deterministic `set()` paths make a same-version/seed rerun idempotent, and 100-write chunks are a conservative TwinBean policy below Firestore’s documented 10 MiB request ceiling. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] [CITED: https://firebase.google.com/docs/firestore/quotas] [ASSUMED]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Synthetic cohort creation and seed command | API / Backend | Database / Storage | It is privileged tooling with no browser role. |
| Root patient summary | Database / Storage | API / Backend | Lets list reads avoid loading longitudinal streams. |
| EHR and IoT histories | Database / Storage | API / Backend | Separate typed subcollections preserve source and timestamp boundaries. |
| Doctor-only list/detail routes | API / Backend | Database / Storage | FastAPI enforces the verified doctor dependency before repository access. |
| Patient presentation | Browser / Client | API / Backend | Deferred clients receive separate fields and never Firestore access. |

## Standard Stack

| Library / tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `firebase-admin` | existing `>=7,<8`; local venv 7.7.0 | Firestore server client | Firebase lists Python Admin SDK support and `firebase_admin.firestore.client`. [CITED: https://firebase.google.com/docs/firestore/client/libraries] [CITED: https://firebase.google.com/docs/reference/admin/python/firebase_admin.firestore] |
| FastAPI + `require_doctor` | existing FastAPI `>=0.117,<1` | Protected patient endpoints | Reuses the verified role gate. [VERIFIED: backend/pyproject.toml:10-15] `"fastapi>=0.117,<1"` and `"firebase-admin>=7,<8"`; [VERIFIED: backend/app/auth.py:35-41] `if claims.get("role") != "doctor":` |
| pytest + `TestClient` | existing `pytest>=8,<9` | Offline unit/route tests | Existing tests monkeypatch Firebase verification. [VERIFIED: backend/tests/test_auth.py:10-23] `monkeypatch.setattr(... "verify_firebase_token" ...)` |

**Installation:** none. The existing Admin SDK includes `google-cloud-firestore` in this venv. [VERIFIED: 2026-10-03 backend venv pip metadata] `Version: 7.7.0` and `Requires: ... google-cloud-firestore ...`.

## Package Legitimacy Audit

No Phase-2 package installation is proposed, so the package-install legitimacy gate does not apply.

## Architecture Patterns

### System Architecture Diagram

```text
explicit seed command -> pure deterministic generator -> validated manifest
                   -> Firestore repository -> patients/{patient_id}
                                            -> ehr_events/{event_id}
                                            -> iot_observations/{event_id}

doctor browser -> Firebase bearer token -> FastAPI + require_doctor
                                      -> repository -> {patient, ehr_history, iot_observations}
```

### Recommended Project Structure

```text
backend/app/firestore.py       # Firestore client factory using get_firebase_app()
backend/app/synthetic_data.py  # pure models + deterministic generator
backend/app/patients.py        # repository reads/writes
backend/app/patient_routes.py  # protected list/detail routes
backend/scripts/seed_synthetic_data.py
backend/tests/test_synthetic_data.py
backend/tests/test_patients.py
backend/tests/test_patient_routes.py
```

### Root summary + two typed streams

Use proposed paths `patients/{patient_id}`, `patients/{patient_id}/ehr_events/{event_id}`, and `patients/{patient_id}/iot_observations/{event_id}`. Root fields contain only synthetic identity, CKD/cohort summary, and provenance; each event contains its own timestamp and source metadata. [ASSUMED] Firestore supports this subcollection shape and eventual collection-group querying. [CITED: https://firebase.google.com/docs/firestore/data-model]

List root summaries with deterministic `order_by(...).limit(...)`; for detail read the root plus separately ordered EHR and IoT queries, returning separately named fields. The Python Firestore API provides `order_by`, `limit`, and `stream`. [CITED: https://docs.cloud.google.com/python/docs/reference/firestore/latest/google.cloud.firestore_v1.base_query.BaseQuery]

### Pure generator + manifest-driven seed

`generate_cohort(seed, generator_version, time_basis)` must return typed records without importing Firebase. Derive stable patient/event IDs from seeded inputs; attach synthetic marker, generator version, seed, and UTC generation/event timestamps. [ASSUMED] The command first validates every output path as TwinBean-owned, then uses explicit-ID `batch.set` operations. Firebase documents explicit IDs and atomic Python write batches. [CITED: https://firebase.google.com/docs/firestore/manage-data/add-data] [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions]

Use an operational cap of 100 manifest writes per batch and fail early for documents approaching 1 MiB or a request approaching 10 MiB. The sizes are Firestore limits; the 100-write cap is deliberately an application policy, not an asserted platform maximum. [CITED: https://firebase.google.com/docs/firestore/quotas] [ASSUMED]

### Route dependency + repository injection

Every list/detail route depends on the unchanged `require_doctor` and a repository dependency. Tests override the repository with an in-memory fake and monkeypatch token verification, matching the project’s proven isolation approach. [ASSUMED] [VERIFIED: backend/tests/test_auth.py:10-23] `monkeypatch.setattr(... "verify_firebase_token" ...)`.

### Anti-Patterns to Avoid

- Random `.add()` event IDs: a rerun cannot target exactly its own prior records. [ASSUMED]
- Arrays of all observations in the root patient document: expanding data belongs in subcollections and documents have a 1 MiB limit. [CITED: https://firebase.google.com/docs/firestore/data-model] [CITED: https://firebase.google.com/docs/firestore/quotas]
- Collection-wide reset/deletion: deleting a parent document does not delete subcollections and violates D-08. [CITED: https://firebase.google.com/docs/firestore/data-model]
- Treating Admin SDK access as doctor authorization: privileged server clients use IAM rather than Firebase Security Rules, so retain FastAPI authorization. [CITED: https://firebase.google.com/docs/firestore/client/libraries]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Firestore credentials/client | REST signing or browser credential relay | Existing Admin app + `firestore.client()` | Official Admin server client/ADC integration. [CITED: https://firebase.google.com/docs/firestore/quickstart-server] |
| Atomic seed write | Custom transaction/retry mechanism | Python Firestore write batch | Atomic `set`/`update`/`delete` batches are provided. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] |
| Unit-test datastore | Live Firestore in pytest | Pure generator + fake repository | Existing Firebase-boundary monkeypatch pattern. [VERIFIED: backend/tests/test_auth.py:10-23] `monkeypatch.setattr(... "verify_firebase_token" ...)` |

## Common Pitfalls

1. **Firestore import is blocked locally.** The observed import failed with `ImportError: DLL load failed while importing cygrpc: An Application Control policy has blocked this file.` [VERIFIED: 2026-10-03 backend venv Firestore import probe] Add an execution checkpoint to resolve policy/approved runtime before a live seed check; do not replace the existing SDK.

2. **No emulator CLI is installed.** `firebase` and `gcloud` were unavailable in this session. [VERIFIED: 2026-10-03 command availability probe] Fakes are the required automated path; Emulator Suite smoke testing is optional after tooling is approved. Admin SDKs connect when `FIRESTORE_EMULATOR_HOST` is set without `http://`. [CITED: https://firebase.google.com/docs/emulator-suite/connect_firestore]

3. **Speculative indexes.** Single-field indexes are automatic but composite/filtered collection-group queries may need configured indexes. [CITED: https://firebase.google.com/docs/firestore/query-data/index-overview] Add no index until an implemented query requires one; commit any resulting index definition/documentation.

## Code Examples

```python
# Firestore client seam; API use is verified in Firebase's Python docs.
from firebase_admin import firestore
from .firebase import get_firebase_app

def get_firestore_client():
    return firestore.client(app=get_firebase_app())
```

The app factory must remain the only initializer. [VERIFIED: backend/app/firebase.py:7-18] `return firebase_admin.get_app()` and `return firebase_admin.initialize_app(credentials.ApplicationDefault(), options)`; [CITED: https://firebase.google.com/docs/reference/admin/python/firebase_admin.firestore]

```python
# Proposed bounded manifest adapter; `100` is a TwinBean policy.
for chunk in chunks(manifest, size=100):
    batch = client.batch()
    for path, payload in chunk:
        batch.set(client.document(path), payload)
    batch.commit()
```

Use only deterministic owned paths in `manifest`; no generic delete branch. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] [ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The proposed collection IDs/path shape are right for TwinBean. | Architecture | Firestore migration after consumers exist. |
| A2 | A small cohort and bounded list/detail payload are enough for Phase 2. | Architecture | Later evaluation may need generator expansion. |
| A3 | 100 writes is an appropriate conservative application batch cap. | Seeding | Lower performance only; it does not claim a platform limit. |
| A4 | Repository injection is the preferred test seam. | Testing | Another fake boundary may be simpler. |

## Environment Availability

| Dependency | Required By | Available | Version / Evidence | Fallback |
|------------|-------------|-----------|--------------------|----------|
| Backend Python | generator/tests | ✓ | Python 3.12.10; [VERIFIED: 2026-10-03 probe] and [VERIFIED: backend/pyproject.toml:5-14] `requires-python = ">=3.12"` | — |
| Firebase Admin | adapter | ✓ package | 7.7.0. [VERIFIED: 2026-10-03 pip metadata] | — |
| Firestore Python import | live adapter/seed | ✗ | gRPC DLL policy block. [VERIFIED: 2026-10-03 import probe] | fakes only; live check needs remediation. |
| Firebase/gcloud CLI | emulator/index CLI | ✗ | commands unavailable. [VERIFIED: 2026-10-03 probe] | Console/manual setup; no CLI test dependency. |

**Missing dependency with no fallback:** an approved environment where the Firestore gRPC extension loads is required for live seeding and verification.

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest; 7 passed locally. [VERIFIED: 2026-10-03 backend test run] |
| Config | [VERIFIED: backend/pyproject.toml:23-25] `testpaths = ["tests"]` and `addopts = "-q"` |
| Quick run | `backend\\.venv\\Scripts\\python.exe -m pytest tests/test_synthetic_data.py tests/test_patients.py tests/test_patient_routes.py -q` [ASSUMED] |
| Full run | `backend\\.venv\\Scripts\\python.exe -m pytest` [VERIFIED: 2026-10-03 backend test run] |

| Req ID | Behavior | Test Type | File Exists? |
|--------|----------|-----------|-------------|
| FIRE-01 | Fake client receives deterministic Firestore manifest/batches. | unit | ❌ Wave 0 |
| FIRE-05 | 401/403/200 for patient list/detail. | route unit | ❌ Wave 0 |
| DATA-01 | Same inputs reproduce adult CKD synthetic records/provenance. | pure unit | ❌ Wave 0 |
| DATA-02 | IoT generation/storage/response stays separate. | pure + route unit | ❌ Wave 0 |
| DATA-03 | No SQLite use; owned Firestore paths only. | unit/source check | ❌ Wave 0 |

**Wave 0 gaps:** add `test_synthetic_data.py`, `test_patients.py`, and `test_patient_routes.py`; add the live-import environment checkpoint. Per task run focused pytest, per wave run the full suite, and require one manual doctor-token read after Firestore becomes runnable.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Retain `verify_id_token(..., check_revoked=True)`. [VERIFIED: backend/app/auth.py:12-13] `return auth.verify_id_token(token, app=get_firebase_app(), check_revoked=True)` |
| V3 Session Management | yes | Server-side bearer validation; Phase 2 adds no session persistence. [VERIFIED: backend/app/auth.py:16-33] `HTTPBearer(auto_error=False)` |
| V4 Access Control | yes | `require_doctor` on every patient route. [VERIFIED: backend/app/auth.py:35-41] `if claims.get("role") != "doctor":` |
| V5 Input Validation | yes | Typed path/query/response models and generator-config validation. [ASSUMED] |
| V6 Cryptography | no new control | Credentials remain backend-only. [VERIFIED: docs/FIREBASE_SETUP.md] |

## Sources

- [Firebase Firestore Python server quickstart](https://firebase.google.com/docs/firestore/quickstart-server)
- [Firebase Firestore data model](https://firebase.google.com/docs/firestore/data-model)
- [Firebase transactions and batched writes](https://firebase.google.com/docs/firestore/manage-data/transactions)
- [Firebase Firestore quotas](https://firebase.google.com/docs/firestore/quotas)
- [Firebase server client libraries](https://firebase.google.com/docs/firestore/client/libraries)
- [Firebase Firestore Emulator Suite](https://firebase.google.com/docs/emulator-suite/connect_firestore)
- [Google Cloud Firestore Python Query reference](https://docs.cloud.google.com/python/docs/reference/firestore/latest/google.cloud.firestore_v1.base_query.BaseQuery)
- [Firebase index overview](https://firebase.google.com/docs/firestore/query-data/index-overview)

## Metadata

**Confidence:** MEDIUM — Context7 and its CLI were unavailable, so official Firebase/Google sources were fetched through WebSearch; the configured confidence seam classifies verified WebSearch evidence as MEDIUM. TwinBean field/path choices are marked `[ASSUMED]`.

**Valid until:** 2026-10-31; re-run the Firestore import probe before execution.
