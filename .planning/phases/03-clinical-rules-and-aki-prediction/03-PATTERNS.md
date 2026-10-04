# Phase 3: Clinical Rules and AKI Prediction - Pattern Map

**Mapped:** 2026-10-04
**Files analyzed:** 18 proposed new/modified files
**Analogs found:** 15 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Tracked Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/clinical_rules.py` | service/model | transform | `backend/app/synthetic_data.py` | role-match |
| `backend/app/aki_features.py` | service/utility | transform | `backend/app/patients.py` | data-flow match |
| `backend/app/aki_model.py` | service | request-response | none; use `03-AI-SPEC.md` | no analog |
| `backend/app/aki_explanations.py` | service/utility | transform | none; use `03-AI-SPEC.md` | no analog |
| `backend/app/prediction_schemas.py` | model | request-response | `backend/app/patients.py` | role-match |
| `backend/app/prediction_service.py` | service | request-response | `backend/app/patients.py` | role/data-flow match |
| `backend/app/patients.py` | repository | CRUD/batch | `backend/app/patients.py` | exact extension |
| `backend/app/patient_routes.py` | route/controller | request-response | `backend/app/patient_routes.py` | exact extension |
| `backend/app/settings.py` | config | request-response | `backend/app/settings.py` | exact extension |
| `backend/app/synthetic_data.py` | generator/model | batch/transform | `backend/app/synthetic_data.py` | exact extension |
| `backend/scripts/train_aki_model.py` | utility/CLI | batch/file-I/O | `backend/scripts/seed_synthetic_data.py` | role/data-flow match |
| `backend/scripts/evaluate_phase3_contract.py` | utility/CLI | batch/file-I/O | `backend/scripts/seed_synthetic_data.py` | role-match |
| `backend/scripts/verify_eval_manifest.py` | utility/CLI | file-I/O/transform | `backend/scripts/seed_synthetic_data.py` | role-match |
| `backend/tests/test_clinical_rules.py` | test | transform | `backend/tests/test_synthetic_data.py` | test-style match |
| `backend/tests/test_aki_features.py` | test | transform | `backend/tests/test_synthetic_data.py` | test-style match |
| `backend/tests/test_aki_model.py` | test | file-I/O/transform | `backend/tests/test_patients.py` | failure-fixture match |
| `backend/tests/test_prediction_routes.py` | test | request-response/CRUD | `backend/tests/test_patient_routes.py`, `backend/tests/test_patients.py` | exact test-seam match |
| `backend/tests/fixtures/aki_reference_scenarios.json` | test fixture | batch | none | no analog |
| `backend/pyproject.toml` | config | dependency configuration | `backend/pyproject.toml` | exact extension |

The file boundaries above follow the recommended layout in `03-AI-SPEC.md` and `03-RESEARCH.md`. `prediction_service.py` is an implied orchestration seam: it keeps CPU/model failure conversion and DTO validation out of the route and repository. If planning chooses a different name, retain the responsibility split.

## Pattern Assignments

### `backend/app/clinical_rules.py` (service/model, transform)

**Analog:** `backend/app/synthetic_data.py`

Use a pure module with explicit inputs and no Firebase, filesystem, network, or system-clock dependency. Copy the immutable data/value-object style and UTC rejection behavior.

**Pure-module and immutable-model pattern** (`backend/app/synthetic_data.py:1-14`, `50-67`):

```python
"""Pure, deterministic synthetic CKD data generation for TwinBean.

This module deliberately has no Firebase, filesystem, network, or system-clock
dependency. Its only inputs are explicit generator settings.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

@dataclass(frozen=True)
class CohortProvenance:
    synthetic: bool
    generator_version: str
    seed: int
    time_basis: datetime
```

**Strict UTC validation pattern** (`backend/app/synthetic_data.py:21-28`):

```python
def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("time_basis must be timezone-aware UTC")
    return value.astimezone(UTC)
```

Apply this structure to explicit creatinine observations, selected baseline evidence, observation/cutoff time, calculation time, exact KDIGO source/rule version, status, and the creatinine-only limitation. Keep the calculation independent of prediction schemas and features. Tests should cover `0.29/0.30 mg/dL`, `1.49/1.50x`, and exact/just-outside 48-hour and seven-day boundaries.

---

### `backend/app/aki_features.py` (service/utility, transform)

**Analog:** `backend/app/patients.py`

Reuse the repository's fail-closed provenance, parent-ownership, mapping, and UTC validation. Perform these checks before creating a pandas frame or invoking the model.

**Stored provenance gate** (`backend/app/patients.py:351-359`):

```python
def _validate_stored_provenance(data, active, source, patient_id=None):
    if data.get("synthetic") is not True or data.get("source") != source:
        raise ValueError("stored record must have exact TwinBean synthetic provenance")
    if data.get("cohort_id") != active.cohort_id:
        raise ValueError("stored record cohort ownership does not match the active cohort")
    if data.get("generator_version") != active.generator_version or data.get("seed") != active.seed:
        raise ValueError("stored record provenance does not match the active cohort")
    if patient_id is not None and data.get("patient_id") != patient_id:
        raise ValueError("stored child record does not belong to its parent patient")
```

**Typed mapping and UTC gate** (`backend/app/patients.py:381-397`):

```python
def _utc_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("Firestore record timestamps must be UTC datetimes or ISO timestamps")
    if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(None):
        raise ValueError("Firestore record timestamps must be timezone-aware UTC")
    return timestamp.astimezone(UTC)

def _record_data(record):
    value = record.get("data")
    if not isinstance(value, Mapping):
        raise ValueError("Firestore record data must be a mapping")
    return dict(value)
```

Build separate cutoff-safe EHR and IoT snapshots (`timestamp <= cutoff`), reject invalid/future/unknown records, then derive exactly the manifest-ordered combined-stream allowlist. Include the reviewed IoT-derived `latest_systolic_bp_mmhg` feature with its `mmHg` unit contract; do not pass patient/scenario IDs, labels, future observations, rule results, or extra columns to sklearn. Version the 24-hour freshness policy rather than hiding it in a literal.

---

### `backend/app/prediction_schemas.py` (model, request-response)

**Analog:** `backend/app/patients.py`

Use Pydantic `BaseModel` at API/repository boundaries as established by `PatientSummary` and `PatientDetail`.

**Separate response-model pattern** (`backend/app/patients.py:36-50`):

```python
class PatientSummary(BaseModel):
    patient_id: str
    display_name: str
    age: int
    ckd_stage: str

class PatientDetail(BaseModel):
    patient: PatientSummary
    ehr_history: list[EhrEvent]
    iot_observations: list[IotObservation]
```

For Phase 3, follow the stronger locked discriminated union in `03-AI-SPEC.md:284-330`: available requires `status="available"`, `outcome="new_aki_within_24h"`, bounded probability, cutoff/generated timestamps, model/schema/freshness versions, warnings, and SHAP attributions; unavailable requires at least one reason and defines no probability or attributions. Define the clinical-rule DTO separately; do not use one shared result type.

---

### `backend/app/aki_model.py` and `backend/app/aki_explanations.py` (services, transform/request-response)

**Analog:** No in-repository ML or explanation implementation exists.

Use `03-AI-SPEC.md:118-268` directly for the sklearn/XGBoost pipeline, manifest-ordered frame, `predict_proba`, exact transformed feature names/order, `TreeExplainer(model_output="raw")`, and raw-margin additivity tolerance `1e-6`.

Still copy these repository conventions:

- explicit, versioned inputs rather than globals (`backend/app/synthetic_data.py:207-224`);
- validate completely before side effects (`backend/app/patients.py:126-146`);
- SHA-256 canonical JSON/checksum construction (`backend/app/patients.py:473-479`);
- fail closed with stable reason codes so the service can create an unavailable DTO.

The release configuration, never request data, selects `pipeline.joblib`, `manifest.json`, and `feature-schema.json`. Verify controlled path, every checksum, exact feature order, cohort/generator snapshot, model/schema/freshness/explanation versions, and package versions before deserialization. Explanation failure invalidates the whole forecast.

---

### `backend/app/prediction_service.py` (service, request-response)

**Analog:** `backend/app/patients.py`

Use the repository's ordered orchestration pattern: load and validate the active immutable cohort, calculate pure values, validate output DTOs, then persist. Do not perform CPU-bound model/SHAP work inside a Firestore transaction. In async route usage, offload the bounded synchronous inference/explanation call with `anyio.to_thread.run_sync` as required by `03-AI-SPEC.md:335-337`.

**Validate-before-write sequence** (`backend/app/patients.py:126-146`):

```python
relative_manifest = self._build_manifest(cohort)
cohort_id = _cohort_id(relative_manifest)
manifest = _versioned_manifest(cohort_id, relative_manifest)
checksum = _manifest_checksum(manifest)
descriptor = _cohort_descriptor(cohort, cohort_id, checksum)
for chunk in _batch_chunks([*manifest, (_cohort_path(cohort_id), descriptor)]):
    batch = self._client.batch()
    for path, payload in chunk:
        batch.set(self._client.document(path), payload)
    batch.commit()
```

Phase 3's operation is smaller: validate exactly one rule DTO and one available-or-unavailable prediction DTO, then hand both to one repository batch. Artifact, feature, model, and SHAP exceptions become sanitized unavailable reason codes, never probability `0.0`; a rule calculation remains independent of forecast availability.

---

### `backend/app/patients.py` (repository, CRUD/batch)

**Analog:** Exact extension of `backend/app/patients.py`.

Resolve the patient only under the active immutable cohort and keep separate subcollections beneath its document.

**Active cohort and separate-stream read pattern** (`backend/app/patients.py:101-124`):

```python
active = self._load_active_cohort()
if active is None:
    return None
document = self._cohort_document(active.cohort_id).collection("patients").document(patient_id)
root_data = document.get().to_dict()
if root_data is None:
    return None
ehr_events = document.collection("ehr_events").order_by("event_time").limit(bounded_limit).stream()
iot_observations = document.collection("iot_observations").order_by("observed_at").limit(bounded_limit).stream()
```

Add `clinical_rules/{result_id}` and `aki_predictions/{result_id}` as separate TwinBean-owned paths. Result IDs should be deterministic from immutable cohort/patient/cutoff/version inputs, following `_stable_id`/checksum conventions, and payloads must repeat ownership/provenance metadata.

**Atomic two-document result write:** create one `client.batch()`, call `batch.set()` for the rule document and prediction document, then one `batch.commit()`. Do not call `_activate`, update `ACTIVE_COHORT_PATH`, delete prior results, or write either result independently. The existing active pointer transaction (`backend/app/patients.py:156-172`) is an explicit anti-analog for result creation because no read-modify-write is required.

---

### `backend/app/patient_routes.py` (route/controller, request-response)

**Analog:** Exact extension of `backend/app/patient_routes.py`.

**Authorization-before-repository dependency pattern** (`backend/app/patient_routes.py:13-24`):

```python
def get_patient_repository() -> PatientRepository:
    return PatientRepository.from_firestore()

@router.get("/patients", response_model=list[PatientSummary])
def list_patients(
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PatientSummary]:
    return repository.list_patients(limit)
```

**Stable path and typed 404 pattern** (`backend/app/patient_routes.py:27-36`):

```python
@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
) -> PatientDetail:
    detail = repository.get_patient(patient_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return detail
```

Every generate/read endpoint must list `Depends(require_doctor)` directly before the repository dependency, use the existing patient ID regex, expose a concrete Pydantic response model, and never accept artifact paths or raw feature dictionaries from the browser. Prefer a bounded `POST` for generation with a timezone-aware cutoff body and separate bounded `GET`s for stored rules/predictions.

---

### `backend/app/settings.py` and `backend/pyproject.toml` (config)

**Analogs:** Exact extensions.

Settings remain an immutable dataclass populated from backend environment variables (`backend/app/settings.py:9-24`). Add controlled model-artifact directory and concurrency/freshness policy selection here only if runtime-configurable; do not expose them through request data. Do not put credentials or service-account material in settings returned to clients.

Add the user-authorized, compatible bounded ML dependencies to the existing project dependency list (`backend/pyproject.toml:5-15`) and preserve pytest configuration (`backend/pyproject.toml:17-25`). Before installing pandas `3.0.6`, scikit-learn `1.9.1`, XGBoost `3.4.1`, and SHAP `0.52.0`, verify their official project identity, exact versions, provenance, and resolver compatibility and record that evidence; explicit authorization removes the interactive checkpoint but not these checks.

---

### `backend/app/synthetic_data.py` (generator/model, batch/transform)

**Analog:** Exact extension of `backend/app/synthetic_data.py`.

Preserve pure deterministic generation from explicit `seed`, `generator_version`, `time_basis`, and count (`backend/app/synthetic_data.py:207-224`), stable UUID5 identifiers (`31-33`), immutable payload mappings (`36-37`), and explicit synthetic source/version/seed on every record (`249-284`, `286-313`).

The current monthly labs and weekly IoT cadence (`268-298`) are too sparse for honest 48-hour rules and a 24-hour freshness policy. Add the smallest deterministic daily terminal scenario extension (at least eight days of creatinine plus cutoff-aligned blood-pressure observations) without using the system clock. Outcome labels must be constructed outside model features from a new event strictly in `(cutoff, cutoff + 24h]`.

---

### Training and evaluation CLIs (utility, batch/file-I/O)

**Analog:** `backend/scripts/seed_synthetic_data.py`

**Explicit argparse entry-point pattern** (`backend/scripts/seed_synthetic_data.py:52-85`):

```python
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed TwinBean's deterministic synthetic CKD cohort into Firestore.")
    parser.add_argument("--seed", required=True, type=_non_negative_seed)
    parser.add_argument("--generator-version", required=True, type=_generator_version)
    return parser

def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    # explicit work only here

if __name__ == "__main__":
    main()
```

`train_aki_model.py`, `evaluate_phase3_contract.py`, and `verify_eval_manifest.py` must be import-safe and run only through `main`. Validate every CLI argument with small argparse type helpers, use explicit seeds/snapshot IDs/paths, and print only sanitized counts, versions, checksums, pass/fail counts, and output digests. Training writes a versioned bundle only after all components and manifest checksums are complete. Evaluation writes actual results only; never placeholders or fabricated metrics.

---

### Test files (test, transform/request-response/CRUD)

**Analogs:** `backend/tests/test_synthetic_data.py`, `backend/tests/test_patients.py`, `backend/tests/test_patient_routes.py`

**Determinism and boundary-fixture style** (`backend/tests/test_synthetic_data.py:14-35`, `101-115`):

```python
def _serialized_cohort(seed: int) -> str:
    cohort = generate_cohort(seed=seed, generator_version="2026.1", time_basis=TIME_BASIS, patient_count=4)
    return json.dumps(cohort.to_dict(), sort_keys=True, separators=(",", ":"))

def test_same_inputs_produce_byte_equivalent_stable_cohort() -> None:
    assert _serialized_cohort(41) == _serialized_cohort(41)
    assert _serialized_cohort(41) != _serialized_cohort(42)
```

Use fixed UTC constants and parameterized exact-boundary cases. Independently author expected rule statuses/reason codes in `aki_reference_scenarios.json`; do not generate expectations by invoking production code.

**Fake Firestore and injected failure pattern** (`backend/tests/test_patients.py:63-109`, `145-179`):

```python
class Batch:
    def commit(self) -> None:
        self.client.batch_commits += 1
        if self.client.fail_batch == self.client.batch_commits:
            raise RuntimeError("simulated batch failure")
        for path, payload in self.set_calls:
            self.client.documents[path] = payload

with pytest.raises(RuntimeError, match="batch"):
    repository.write_cohort(...)
assert _active(client)["cohort_id"] == original.cohort_id
```

Extend this fake rather than introducing an emulator dependency. For prediction result batches, make commit atomic in the fake (stage calls, then apply together) and inject failure before either write is applied. Assert neither result exists, the active pointer is unchanged, prior versions remain, and unrelated documents are untouched.

**Route dependency override and authorization short-circuit pattern** (`backend/tests/test_patient_routes.py:28-42`, `130-150`, `179-216`):

```python
app.dependency_overrides[get_patient_repository] = lambda: repository
yield repository
app.dependency_overrides.clear()

response = client.get("/patients")
assert response.status_code == 401
assert fake_repository.limits == []
```

Test doctor success plus missing, invalid, and non-doctor tokens, always asserting the repository/service was not called on denial. Test exact serialized key sets so current rule and future prediction fields cannot bleed into one another. Test unavailable responses contain reasons and omit probability/attributions.

## Shared Patterns

### Exact Doctor Authorization

**Source:** `backend/app/auth.py:16-41`  
**Apply to:** Every clinical-rule, prediction-generation, and stored-result route.

```python
claims = verify_firebase_token(credentials.credentials)
if claims.get("role") != "doctor":
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access is required.")
```

Do not duplicate or weaken this check. Browser state and mere token validity are insufficient.

### Active Immutable Cohort and Provenance

**Source:** `backend/app/patients.py:174-222`, `351-359`  
**Apply to:** Feature construction, rule calculation, prediction orchestration, and result persistence.

Always resolve `twinbean_metadata/active_cohort`, validate it against its staged descriptor/manifest, and operate beneath `twinbean_cohorts/{cohort_id}/patients/{patient_id}`. Accept only exact TwinBean synthetic sources, matching generator version/seed, matching cohort ownership, and matching parent patient.

### Separate Clinical Contracts

**Sources:** `backend/app/patients.py:45-50`; `backend/tests/test_patient_routes.py:187-196`  
**Apply to:** Schemas, routes, repository paths, tests, and later UI consumers.

The project already keeps EHR and IoT as independently named fields and asserts the absence of a combined `history`. Follow the same explicit separation for `clinical_rules` and `aki_predictions`; never create a generic combined clinical-result payload.

### Validate Before Side Effects

**Source:** `backend/app/patients.py:126-146`, `270-291`, `447-470`  
**Apply to:** Artifact release, result generation, and Firestore writes.

Construct and validate typed DTOs, paths, ownership, provenance, document size, and checksums before opening the one result batch. Bound all reads/writes. Preserve prior versions; no collection-wide cleanup or generated Firestore IDs.

### Atomic Firestore Result Write

**Source:** `backend/app/patients.py:137-142`; failure tests at `backend/tests/test_patients.py:145-179`  
**Apply to:** One rule plus one prediction for a patient/cutoff.

Use one batch with two deterministic `set` calls and one commit. The active pointer transaction is not part of this operation. A failed commit must leave both result paths absent and all cohort metadata unchanged.

### Stable IDs, Canonical Serialization, and Checksums

**Sources:** `backend/app/synthetic_data.py:27-37`; `backend/app/patients.py:473-479`  
**Apply to:** result IDs, artifact manifests, feature schemas, training/evaluation manifests, and reproducibility tests.

Use stable UUID5 IDs or SHA-256 of canonical, sorted JSON. Include version, seed/snapshot, cutoff, schema, and model identifiers in the immutable identity inputs. Never use wall-clock time as the sole identity.

### Failure Semantics

**Sources:** repository validation raises specific `ValueError`s (`backend/app/patients.py:330-397`); locked union in `03-AI-SPEC.md:284-330`.  
**Apply to:** feature, artifact, model, and explanation boundaries.

Authorization failures remain HTTP 401/403. Missing patients use the established typed 404. Clinical/model precondition failures become a validated, persisted unavailable prediction with stable sanitized reasons and no numeric probability/attributions. Do not swallow repository corruption or translate it into low risk.

## No Analog Found

| File | Role | Data Flow | Reason / Planner Direction |
|---|---|---|---|
| `backend/app/aki_model.py` | service | request-response | No existing ML pipeline or artifact loader. Implement directly from `03-AI-SPEC.md:118-268`; retain project validation/checksum conventions. |
| `backend/app/aki_explanations.py` | service/utility | transform | No explanation code exists. Implement TreeExplainer raw-margin alignment/additivity exactly from the AI spec. |
| `backend/tests/fixtures/aki_reference_scenarios.json` | test fixture | batch | No JSON reference-set convention exists. Use canonical JSON, explicit schema/rubric version, synthetic provenance, reviewer/source metadata, and independently authored expected outputs. |

## Planner Warnings

- The ML package versions in research were marked `SUS` by a conservative legitimacy gate, but the user pre-authorized the named official packages. Do not insert an interactive checkpoint; require official identity, exact-version, provenance, and resolver checks before dependency installation or lockfile modification.
- The current generator cannot support fresh 48-hour criteria; generator/scenario fixtures must precede claims of valid inference.
- Do not plan formal EHR-only versus combined held-out evaluation, calibration/performance claims, dashboard ranking, or patient-detail UI here; those belong to later phases.
- Do not use current rule output as a feature, and do not allow a successful numeric score to survive artifact or SHAP failure.
- Preserve the exact response invariants from the AI spec; unavailable must not define probability or attributions.

## Metadata

**Analog search scope:** `backend/app`, `backend/scripts`, `backend/tests`, `backend/pyproject.toml`, Phase 2 summaries and pattern map  
**Tracked-source gate:** all named code analogs verified through `git ls-files`; no runtime/install mirrors are referenced  
**Primary analog files read:** 9 source/config files, 3 tests, 4 Phase 2 summaries  
**Pattern extraction date:** 2026-10-04
