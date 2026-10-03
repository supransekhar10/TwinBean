# Phase 2 Firestore API and Source Coverage

**Status:** Planning contract; live persistence/read proof pending  
**Scope:** Firebase Admin / Cloud Firestore operations used by Phase 2  
**Boundary:** Backend-only; browser code never receives a Firestore client or privileged credential

## Firestore API coverage matrix

| Admin / Firestore surface | Decision | Plan | Verification | Reason |
|---|---|---|---|---|
| `firebase_admin.firestore.client(app=get_firebase_app())` | IN | 02-01 Task 1; 02-04 Task 2 | Lazy-import seam is automated; live import is planned and pending at the 02-04 approved-runtime checkpoint | Reuses the single Phase 1 Admin app and Application Default Credentials. |
| `Client.collection("patients")` | IN | 02-01 Task 1 | Fake-client list-query assertion | Root documents provide bounded cohort summaries without loading event history. |
| `CollectionReference.order_by(...).limit(...).stream()` | IN | 02-01 Task 1 | Repository query-shape tests | Provides deterministic, bounded patient listing. |
| `Client.document(path)` / `DocumentReference.get()` | IN | 02-02 Task 2; 02-03 Task 1 | Explicit-path fake assertions and detail-read tests | Deterministic owned paths support idempotent writes and direct patient lookup. |
| `DocumentReference.collection("ehr_events")` | IN | 02-02 Task 2; 02-03 Task 1 | Separate path/query assertions | Preserves EHR history as its own typed stream. |
| `DocumentReference.collection("iot_observations")` | IN | 02-02 Task 2; 02-03 Task 1 | Separate path/query assertions | Preserves simulated IoT observations as an independent typed stream. |
| `Client.batch()` / `WriteBatch.set()` / `WriteBatch.commit()` | IN | 02-02 Task 2; 02-04 Task 2 | Fake batch tests and repeat-seed equality are automated; live rerun is planned and pending at the 02-04 checkpoint | Enables bounded idempotent writes to explicit TwinBean-owned document IDs. |
| `CollectionReference.add()` | OPT-OUT | 02-02 Task 2 | Source/test assertion | Generated document IDs would prevent deterministic reruns from targeting the same records. |
| `DocumentReference.delete()` / recursive delete helpers | OPT-OUT | 02-02 Task 2 | Fake client exposes failure-on-delete and tests assert it is never called | Phase 2 may not broadly delete or reset Firestore data. |
| `DocumentReference.update()` / `create()` | OPT-OUT | 02-02 Task 2 | Write manifest asserts `set()` only | `set()` against deterministic owned IDs is the required idempotent operation. |
| Transactions | OPT-OUT | 02-02 Task 2 | Repository surface audit | The seed is a deterministic manifest write with no read-modify-write invariant. |
| `bulk_writer()` | OPT-OUT | 02-02 Task 2 | Repository surface audit | The small bounded cohort fits conservative 100-write batches without another execution model. |
| Collection-group queries | OPT-OUT | 02-03 Task 1 | Repository surface audit | Phase 2 reads one patient's named subcollections directly; cross-patient event queries are not required. |
| `where(...)` filters / composite indexes | OPT-OUT | 02-01 Task 1; 02-03 Task 1 | Query-shape tests | Root listing and direct detail reads need only ordering and limits, so no speculative index is added. |
| Realtime listeners / `on_snapshot()` | OPT-OUT | 02-03 Task 1 | Repository surface audit | Phase 2 exposes request/response reads, not subscriptions. |
| Browser Firestore SDK | OPT-OUT | 02-01 Task 1; 02-04 Task 1 | Backend route tests and documentation/source audit | D-10 requires all patient access to cross the FastAPI doctor-authorization boundary. |

## Specless planner assumptions and acceptance tests

| Requirement | Explicit assumption | Concrete acceptance test |
|---|---|---|
| FIRE-01 | The existing Firebase Admin app plus a lazily imported `firestore.client(app=...)` is the sole Firestore client boundary. | Fake repository/client tests cover every operation above; 02-04 Task 2 plans the same import and one live seed/read in an approved runtime. That checkpoint is pending, not verified. |
| FIRE-05 | Applying the unchanged `require_doctor` dependency to every patient list/detail handler is the authorization boundary; repository access is never exposed directly to the browser. | Route tests prove missing/invalid token `401`, non-doctor `403`, exact doctor `200`, and no repository call before authorization succeeds. |
| DATA-01 | A deterministic pure generator can provide clinically plausible adult CKD histories without any real-patient source material. | Same inputs produce byte-equivalent models and stable IDs; tests assert age at least 18, CKD context, encounters, medications, kidney labs, and synthetic provenance. |
| DATA-02 | Simulated home measurements remain independent when generation, storage, repository reads, and API serialization use separate types and fields. | Tests assert distinct EHR/IoT types, IDs, subcollections, timestamp/source metadata, and response keys `ehr_history` and `iot_observations`. |
| DATA-03 | Phase 2 establishes Cloud Firestore as the authoritative store for the in-scope patient/EHR/IoT subset; rule and prediction records remain absent until Phase 3 creates real outputs. | Tests assert only Firestore-owned paths and no SQLite dependency or adapter; 02-04 Task 2 is the pending live checkpoint for persisted patient/EHR/IoT documents without rule or prediction values. |

## Multi-source coverage audit

| Source | ID | Feature / constraint | Plan | Status | Notes |
|---|---|---|---|---|---|
| GOAL | — | Authorized doctors access synthetic CKD histories and a separately modeled IoT stream stored in Firestore. | 02-01, 02-02, 02-03, 02-04 | COVERED | Offline implementation is planned across 02-01 through 02-03; live persistence/read proof remains pending at 02-04 Task 2. |
| REQ | FIRE-01 | Backend Firestore access uses Firebase Admin SDK. | 02-01, 02-02, 02-04 | COVERED | Offline seam is planned; required live verification is pending at 02-04 Task 2. |
| REQ | FIRE-05 | Only authorized doctors can access patient data. | 02-01, 02-03, 02-04 | COVERED | Exact Phase 1 guard remains unchanged; live doctor-token proof is pending at 02-04 Task 2. |
| REQ | DATA-01 | Reproducible synthetic adult CKD histories. | 02-02 | COVERED | Pure versioned generator and deterministic tests. |
| REQ | DATA-02 | Independently modeled simulated IoT stream. | 02-02, 02-03 | COVERED | Separate types, paths, queries, and response fields. |
| REQ | DATA-03 | Firestore is authoritative rather than SQLite. | 02-02, 02-04 | COVERED | Owned Firestore manifest and operational docs are planned; live evidence remains pending at 02-04 Task 2. |
| RESEARCH | R-01 | Reuse Admin app; no new dependency or initializer. | 02-01 | COVERED | Lazy import accommodates the local `cygrpc` block. |
| RESEARCH | R-02 | Root summary plus `ehr_events` and `iot_observations` subcollections. | 02-01, 02-02, 02-03 | COVERED | List reads roots only; detail reads streams independently. |
| RESEARCH | R-03 | Pure generator and explicit manifest-driven seed command. | 02-02 | COVERED | No API-startup seeding. |
| RESEARCH | R-04 | Explicit IDs, `set()` writes, 100-write batches, and size guards. | 02-02 | COVERED | Fake client proves the exact manifest and rerun behavior. |
| RESEARCH | R-05 | Repository injection and offline Firebase-boundary tests. | 02-01, 02-02, 02-03 | COVERED | No test requires a live Firestore import. |
| RESEARCH | R-06 | Local `cygrpc` block requires an approved-runtime live checkpoint. | 02-04 | COVERED | Blocking-human and non-destructive; the checkpoint remains pending and the SDK is not swapped. |
| RESEARCH | R-07 | Avoid speculative indexes, emulator dependency, and package installs. | 02-01, 02-02, 02-04 | COVERED | Native existing dependency and simple bounded queries only. |
| CONTEXT | D-01 | Versioned deterministic generator, seed, stable patient IDs. | 02-02 | COVERED | Cited in generator task. |
| CONTEXT | D-02 | Plausible adult CKD demographics, context, encounters, medications, and kidney labs. | 02-02 | COVERED | Cited in generator task. |
| CONTEXT | D-03 | Explicit synthetic provenance, version, seed, UTC timestamps, and no real data. | 02-02 | COVERED | Cited in generator task. |
| CONTEXT | D-04 | Root identity/summary separate from longitudinal observations. | 02-01, 02-02 | COVERED | Cited in repository tasks. |
| CONTEXT | D-05 | EHR and IoT use distinct typed subcollections. | 02-02, 02-03 | COVERED | Costly decision rating retained. |
| CONTEXT | D-06 | IoT home monitoring remains distinct from EHR clinical history/labs. | 02-02 | COVERED | Cited in generator task. |
| CONTEXT | D-07 | Explicit backend seed command; never seed on API startup. | 02-02, 02-04 | COVERED | Cited in seed and docs tasks. |
| CONTEXT | D-08 | Idempotent same-input seed writes only owned paths and never broadly deletes. | 02-02, 02-04 | COVERED | Cited in writer and pending live check. |
| CONTEXT | D-09 | Firestore is authoritative; no SQLite/browser persistence. | 02-02, 02-04 | COVERED | Cited in repository and docs tasks. |
| CONTEXT | D-10 | Browser access goes through FastAPI, never Firestore directly. | 02-01, 02-04 | COVERED | Cited in route and docs tasks. |
| CONTEXT | D-11 | Patient list/detail use unchanged `require_doctor`. | 02-01, 02-03 | COVERED | Cited in both route tasks. |
| CONTEXT | D-12 | API returns separately named EHR and IoT fields. | 02-03 | COVERED | Cited in detail task. |

Deferred clinical rules, AKI prediction, SHAP output, dashboard ordering, and patient-detail presentation are excluded by the Phase 2 context and are not audit gaps.
