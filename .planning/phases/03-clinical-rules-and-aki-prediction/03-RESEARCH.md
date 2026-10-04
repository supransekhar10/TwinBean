# Phase 3: Clinical Rules and AKI Prediction - Research

**Researched:** 2026-10-04  
**Domain:** Deterministic creatinine-only AKI rules, time-safe tabular inference, and audited Firestore result persistence  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Clinical Rule Contract
- Implement deterministic, versioned AKI calculations from authoritative KDIGO creatinine criteria; cite the exact source and rule version in every result.
- Report only criteria supported by available synthetic inputs. Do not imply urine-output assessment unless that input is explicitly generated and validated.
- A rule result describes current/observed clinical status and is never used as the future prediction response shape.
- Persist rule inputs, observation time, calculation time, status, evidence, source, version, and limitations under the active immutable cohort.

### Prediction Semantics
- Predict a new AKI event within the 24 hours after an explicit prediction cutoff for synthetic adults with CKD.
- A valid result includes probability, prediction time/cutoff, model/version identifiers, input freshness, data-quality warnings, and separate SHAP feature attributions.
- Missing required features, invalid units/types, records after the cutoff, stale inputs, model incompatibility, or explanation failure produce an explicit unavailable result with reasons; never substitute probability `0`.
- Keep scenario IDs, patient IDs, future observations, outcome labels, clinical-rule outputs, and other leakage-prone metadata out of model feature vectors.

### Modeling and Artifacts
- Use scikit-learn-compatible preprocessing and XGBoost for the production research model; SHAP explains the implemented model without causal language.
- Training is reproducible from explicit seeds and creates versioned, checksum-verifiable artifacts and a feature schema. Do not deserialize untrusted model artifacts.
- Phase 3 may produce the model needed for inference, but formal patient-level EHR-only versus combined-stream evaluation and its actual report remain Phase 6.
- Tests must exercise valid inference, unavailable states, cutoff enforcement, feature allowlisting, current-rule/prediction separation, persistence, and explanation integrity.

### Firestore and Authorization
- Extend the Phase 2 active-cohort repository rather than creating a parallel database or SQLite path.
- Store rule and prediction outputs in separate TwinBean-owned subcollections beneath the immutable cohort/patient namespace.
- All read/inference endpoints remain backend-only and require exact `role: doctor`; browser state never authorizes patient access.
- Preserve old cohort versions and unrelated data; any result generation failure must not corrupt the active cohort or convert unavailable risk into a numeric score.

### the agent's Discretion
- Exact module boundaries, internal DTO names, artifact file format, and bounded endpoint shapes may follow existing FastAPI/Pydantic patterns.
- Choose a documented freshness threshold that fits the generated stream cadence and test it explicitly; expose it as versioned configuration rather than a hidden constant.
- Choose the smallest synthetic scenario extension needed to support honest training labels and inference without claiming clinical realism.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

- Doctor dashboard ranking and summary states: Phase 4.
- Patient detail charts, replay controls, and separate visual sections: Phase 5.
- Final comparative evaluation report and metrics: Phase 6.
- Optional AI copilot: outside the core prediction path and not required for this milestone.
</user_constraints>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRED-01 | Predict a new AKI within 24 hours for an adult with CKD. | Deterministic scenario/label construction makes the positive label strictly post-cutoff and synthetic-only. |
| PRED-02 | Use scikit-learn and XGBoost, handling invalid, missing, or stale inputs explicitly. | Pipeline, versioned feature contract, artifact verification, and unavailable preflight are prescriptive below. |
| PRED-03 | Preserve unavailable as distinct from zero risk. | Use the locked discriminated response union and persist unavailable results with reason codes. |
| PRED-04 | Calculate, store, and return rules and predictions as distinct types. | Separate DTOs, subcollections, and atomic two-document result batches prevent conflation. |
| PRED-05 | Produce SHAP attributions for valid predictions. | Use `TreeExplainer` in raw-margin space with exact feature alignment and additivity validation. |

## Project Constraints (from AGENTS.md)

- Use only synthetic patient and simulated IoT data; do not introduce real patient data or PHI.
- Keep Firebase ID-token verification server-side and require the exact `role: doctor` claim on every protected read or inference route.
- Keep Firebase service-account credentials backend-only, out of Git, and never browser-accessible; custom claims remain Admin-SDK-only.
- Continue to use Cloud Firestore as the sole persistence design; do not add SQLite or browser-side Firestore access.
- Keep current clinical-rule status separate from future risk; an invalid forecast is `Risk unavailable`, never a numeric zero.
- Do not represent synthetic development outputs as clinical validation or fabricate evaluation claims; Phase 6 owns formal held-out comparison.
- Follow the bounded implement → check → fix loop; do not weaken tests after failures.

## Summary

Phase 3 should extend the existing active-cohort repository, rather than add another data access path. The backend already validates one active immutable cohort before a patient read, and it has a doctor dependency before its repository dependency. The source-of-truth values are: `[VERIFIED: backend/app/patients.py:25-33]` `COHORTS_COLLECTION = "twinbean_cohorts"`, `ACTIVE_COHORT_PATH = "twinbean_metadata/active_cohort"`, `_EHR_SOURCE = "twinbean-synthetic-ehr"`, and `_IOT_SOURCE = "twinbean-simulated-iot"`; `[VERIFIED: backend/app/patient_routes.py:18-24]` `Depends(require_doctor)` and `Depends(get_patient_repository)`. New work belongs behind that boundary. 

Use KDIGO 2012 creatinine criteria exactly as a *creatinine-only* observed-status calculation: an SCr increase of at least 0.3 mg/dL within 48 hours or to at least 1.5 times baseline within seven days. KDIGO also includes a urine-output criterion, which this input contract cannot claim to have assessed. [CITED: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf] The prediction is a distinct future outcome: a new event strictly after cutoff and within the following 24 hours. [VERIFIED: 03-CONTEXT.md]

The current generator has only monthly laboratory observations and weekly IoT observations, so it cannot honestly produce a fresh 48-hour creatinine comparison at its present terminal time. `[VERIFIED: backend/app/synthetic_data.py:268-277]` `lab_time = basis - timedelta(days=30 * (6 - month))` and `data=_frozen_data({"test_name": test_name, "value": value, "unit": unit})`; `[VERIFIED: backend/app/synthetic_data.py:286-298]` `observed_at = basis - timedelta(days=7 * (8 - week))` with the three independent IoT measurement types. Add a small deterministic terminal scenario series (daily creatinine for at least eight days, plus cutoff-aligned source-specific observations) and derive labels from it outside the feature vector. This creates valid rule, training, and cutoff-adversarial fixtures without implying clinical realism. [ASSUMED]

**Primary recommendation:** implement an explicit time-bounded feature builder and artifact barrier first; only then add a protected `generate results for one patient/cutoff` route that validates and batch-persists one rule document plus one available-or-unavailable prediction document.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| KDIGO creatinine-only rule calculation | API / Backend | Database / Storage | Pure calculation consumes validated EHR evidence and creates traceable immutable result data. |
| Cutoff-safe EHR/IoT feature snapshot | API / Backend | Database / Storage | The backend, not the browser, filters source observations to `<= cutoff`, validates units/freshness, and exposes only reviewed features. |
| XGBoost pipeline, artifact checksum, and SHAP | API / Backend | — | Python libraries are CPU-bound server work; artifact selection and loading must never be requester-controlled. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Rule/prediction result documents | Database / Storage | API / Backend | Distinct subcollections preserve the clinical distinction and support atomic result creation. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] |
| Doctor authorization and bounded endpoint | API / Backend | — | The present FastAPI route pattern enforces authorization before repository access. [VERIFIED: backend/app/patient_routes.py:18-24] `Depends(require_doctor)` and `Depends(get_patient_repository)`. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.12` | Existing backend runtime | `[VERIFIED: backend/pyproject.toml:5-14]` `requires-python = ">=3.12"`; local venv probes Python 3.12.10. |
| `pandas` [WARNING: flagged as suspicious — verify before using.] | `3.0.6` | Typed tabular frame at the feature/pipeline boundary | Locked AI-SPEC candidate pin; PyPI listed it and the conservative legitimacy gate returned `SUS`. The user has pre-authorized this named official package, subject to official identity, exact-version, and provenance verification before use. [ASSUMED] |
| `scikit-learn` [WARNING: flagged as suspicious — verify before using.] | `1.9.1` | `Pipeline`, `ColumnTransformer`, and fit-only-on-training preprocessing | Official persistence guidance requires matching versions and trusted artifacts. The user has pre-authorized this named official package, subject to official identity, exact-version, and provenance verification before use. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| `xgboost` [WARNING: flagged as suspicious — verify before using.] | `3.4.1` | `XGBClassifier` for the local binary predictor | Official docs support the scikit-learn estimator interface and JSON/UBJSON model formats. The user has pre-authorized this named official package, subject to official identity, exact-version, and provenance verification before use. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html] |
| `shap` [WARNING: flagged as suspicious — verify before using.] | `0.52.0` | Tree-model attribution for available predictions only | `TreeExplainer` supports XGBoost and its documented additivity check. The user has pre-authorized this named official package, subject to official identity, exact-version, and provenance verification before use. [CITED: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html] |

### Supporting

| Library / project facility | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic v2 / FastAPI | Existing compatible range | Discriminated available/unavailable DTOs and protected response models | At every repository and route boundary. `[VERIFIED: backend/pyproject.toml:10-14]` `"fastapi>=0.117,<1"`. |
| Firebase Admin / Firestore | Existing `>=7,<8` | Active cohort read and bounded atomic result write | Keep all Firestore access server-side. `[VERIFIED: backend/pyproject.toml:10-14]` `"firebase-admin>=7,<8"`. |
| pytest | Existing `>=8,<9` | Pure-domain, fake-Firestore, route, and artifact tests | Use focused tests per task and the entire backend suite per wave. `[VERIFIED: backend/pyproject.toml:17-25]` `"pytest>=8,<9"`, `testpaths = ["tests"]`, `addopts = "-q"`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `joblib`-serialized whole sklearn pipeline | Native XGBoost JSON/UBJSON plus a separately versioned preprocessing contract | XGBoost JSON/UBJSON preserves model feature names, but it cannot by itself serialize the sklearn preprocessing object. Retain the AI-SPEC controlled `pipeline.joblib` bundle only after checksum/version verification; do not accept an untrusted artifact. [CITED: https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html] [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Firestore batch for the two result documents | Firestore transaction | No read-modify-write is needed for immutable result IDs. A batch is atomic and avoids transaction callback retries; retain the existing transaction only for active-pointer publication. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] |

**Installation (after official package identity, exact-version, and provenance verification):**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install "pandas==3.0.6" "scikit-learn==1.9.1" "xgboost==3.4.1" "shap==0.52.0"
```

The exact candidate pins are locked in the AI-SPEC. `[VERIFIED: 03-AI-SPEC.md:131-137]` `python -m pip install "pandas==3.0.6" "scikit-learn==1.9.1" "xgboost==3.4.1" "shap==0.52.0"`. A 2026-10-04 registry query found those versions, while the installed backend lacks the ML packages; an attempted full `pip install --dry-run` timed out before dependency resolution completed. [ASSUMED]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `pandas` | PyPI | Registry signal: 2026-09-17 publication [ASSUMED] | unavailable to gate | unavailable to gate | SUS | User-authorized named official package; verify official PyPI identity, exact version, and provenance before install |
| `scikit-learn` | PyPI | Registry signal: 2026-09-10 publication [ASSUMED] | unavailable to gate | unavailable to gate | SUS | User-authorized named official package; verify official PyPI identity, exact version, and provenance before install |
| `xgboost` | PyPI | Registry signal: 2026-08-15 publication [ASSUMED] | unavailable to gate | unavailable to gate | SUS | User-authorized named official package; verify official PyPI identity, exact version, and provenance before install |
| `shap` | PyPI | Registry signal: 2026-05-28 publication [ASSUMED] | unavailable to gate | unavailable to gate | SUS | User-authorized named official package; verify official PyPI identity, exact version, and provenance before install |

**Packages removed due to [SLOP] verdict:** none.  
**Packages flagged as suspicious [SUS]:** `pandas`, `scikit-learn`, `xgboost`, `shap`; the user explicitly pre-authorized these named official packages, so no interactive checkpoint is required. Installation remains conditional on verifying the official project identity, exact pinned version, and provenance and recording that evidence. The registry gate may be conservative; it is not evidence that the packages are malicious. [ASSUMED]

## Architecture Patterns

### System Architecture Diagram

```text
active immutable cohort / patient
        |
        +--> EHR labs ---------+--> KDIGO creatinine-only rule --> validated rule DTO
        |                      |
        +--> IoT observations -+--> cutoff-safe source snapshots --> reviewed feature allowlist
                                                               |             |
doctor token --> require_doctor --> repository/provenance ----+             v
                                                        preflight -> verified artifact -> XGBoost -> SHAP
                                                            |                         |
                                                            +-- failure ------------+--> unavailable DTO
                                                                                      |
validated rule DTO + validated forecast DTO --> one Firestore write batch
        |                                           |
        +--> clinical_rules/{result-id}             +--> aki_predictions/{result-id}
```

The two final paths are proposed TwinBean-owned subcollection names, not existing paths. [ASSUMED]

### Recommended Project Structure

```text
backend/
├── app/
│   ├── clinical_rules.py       # pure KDIGO creatinine-only evidence and result DTO
│   ├── aki_features.py         # cutoff/source/unit/freshness checks and allowlist
│   ├── aki_model.py            # artifact manifest, checksum, compatible pipeline loading
│   ├── aki_explanations.py     # TreeExplainer alignment and raw-margin additivity
│   ├── prediction_schemas.py   # available/unavailable response models
│   ├── patients.py             # extend active-cohort repository and result batches
│   └── patient_routes.py       # protected bounded result-generation/read routes
├── scripts/
│   └── train_aki_model.py      # explicit deterministic training; no startup side effect
└── tests/
    ├── test_clinical_rules.py
    ├── test_aki_features.py
    ├── test_aki_model.py
    └── test_prediction_routes.py
```

### Pattern 1: Deterministic rule result, not a prediction

**What:** Parse only UTC creatinine EHR events with unit `mg/dL`; select explicit prior evidence in the 48-hour and seven-day windows, record baseline method/evidence, and return a creatinine-only limitation. Do not put rule output into the model frame. [CITED: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf]

**When to use:** For every authorized cutoff, independently of whether a model artifact or feature snapshot is valid.

**Implementation contract:** A synthetic scenario is positive only when the patient has no supported AKI rule at cutoff and becomes rule-positive from evidence strictly in `(cutoff, cutoff + 24h]`. The label is the training target `y`, never an input column. [ASSUMED]

### Pattern 2: Cutoff-safe dual-stream snapshot then model-specific allowlist

**What:** Gather EHR and IoT separately; reject rather than silently discard malformed, future-dated, unknown-provenance, or unit-incompatible required observations. Then build an ordered raw model frame only from a manifest allowlist. The Phase-3 inference artifact is a combined-stream contract and includes the meaningful IoT-derived feature `latest_systolic_bp_mmhg` alongside `age_years`, `latest_creatinine_mg_dl`, and `creatinine_delta_48h_mg_dl`. This satisfies PRED-01's combined-stream inference scope without performing the formal EHR-only-versus-combined comparison reserved for Phase 6. The feature schema and artifact manifest must version the four-column order and units. [RESOLVED]

**When to use:** Both in explicit training and request-time inference. Fit imputers only inside the sklearn pipeline on the training partition; request-time absence of a required feature is unavailable, not imputed. [CITED: https://scikit-learn.org/stable/modules/compose.html]

**Freshness policy:** version a 24-hour required-observation maximum age for the initial daily terminal scenario series. Existing monthly/weekly data must therefore become unavailable unless the generator extension supplies a valid recent measurement; do not pick a loose threshold merely to score the old cadence. [ASSUMED]

### Pattern 3: Controlled artifact bundle before deserialization

**What:** The release configuration chooses a fixed local artifact directory; request data supplies neither a file name nor a manifest. Verify manifest JSON/schema, SHA-256 for every bundle member, exact feature order, cohort/generator snapshot, code revision, and installed package versions before `joblib.load`. Any failure returns/persists unavailable and quarantines the bundle. `joblib` is pickle-based and only safe for a trusted verified source; cross-version sklearn loading is unsupported. [CITED: https://scikit-learn.org/stable/model_persistence.html]

**Bundle:** `pipeline.joblib`, `manifest.json`, `feature-schema.json`, and checksums are the smallest safe local bundle consistent with the AI-SPEC. The manifest must name Python, pandas, scikit-learn, XGBoost, SHAP, model, feature-schema, freshness-policy, label, cohort-snapshot, generator, and explanation-mode versions. [ASSUMED]

### Pattern 4: Validate both distinct DTOs, then atomically write exactly two result documents

**What:** Read/validate the active cohort first, calculate a rule, then compute an available or unavailable forecast. Validate both Pydantic DTOs before creating a single bounded Firestore batch that `set`s one immutable rule document and one immutable prediction document. Do not update `twinbean_metadata/active_cohort`; failure leaves old cohort versions and unrelated data untouched. The existing pointer is only published by a separate transaction. `[VERIFIED: backend/app/patients.py:126-146]` `"Stage, read back, validate, then atomically publish one cohort pointer."`, `batch.set(...)`, `batch.commit()`, and `self._activate(active)`; `[VERIFIED: backend/app/patients.py:156-172]` `transaction.set(self._client.document(ACTIVE_COHORT_PATH), ...)` then `transaction.commit()`.

**Why:** Firestore batches either apply all writes or none; transactions can retry after concurrent reads, so CPU-bound generation must not live inside a transaction callback. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions]

### Locked prediction response invariant

The planner must keep the following locked values verbatim in the response models: `[VERIFIED: 03-AI-SPEC.md:301-326]` `status: Literal["available"]`, `outcome: Literal["new_aki_within_24h"]`, `probability: float = Field(ge=0.0, le=1.0)`, `attributions: list[ShapAttribution]`, `status: Literal["unavailable"]`, and `reasons: list[str] = Field(min_length=1)`. The unavailable model must define no probability or attributions. [ASSUMED]

### Anti-Patterns to Avoid

- **Calling a negative creatinine-only result “no AKI”:** it overstates assessment because the available synthetic contract has no validated urine-output evidence. [CITED: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf]
- **Feature filtering by `remainder="drop"` alone:** unknown/leakage-prone fields can be silently ignored instead of rejected; preflight must detect them. [CITED: https://scikit-learn.org/stable/modules/compose.html]
- **Using a current rule result as a prediction feature or label proxy:** it violates the locked observed/future separation. [VERIFIED: 03-CONTEXT.md]
- **Writing rule then prediction in independent commits:** a crash can create an orphaned result. Use one batch after DTO validation. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions]
- **Returning a score when SHAP or artifact checks fail:** it violates the explicit unavailable contract. [VERIFIED: 03-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Imputation/preprocessing boundary | Custom median state and ad-hoc feature transforms | sklearn `Pipeline` + `ColumnTransformer` | Keeps learned preprocessing inside the fitted training pipeline. [CITED: https://scikit-learn.org/stable/modules/compose.html] |
| Tree attribution | Approximate/custom feature-importance math | `shap.TreeExplainer` plus its additivity check | It supports XGBoost, documents raw XGBoost output, and validates sum-to-output. [CITED: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html] |
| Result atomicity/retry | Custom distributed commit/retry protocol | Firestore write batch | Batch writes are an existing atomic server capability. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] |
| Artifact trust policy | Heuristic filename approval | SHA-256 manifest barrier and controlled local selection | Pickle/joblib loading can execute arbitrary code, so only a trusted verified source is acceptable. [CITED: https://scikit-learn.org/stable/model_persistence.html] |

**Key insight:** the safety-critical code is the deterministic boundary around the model—cutoff, provenance, schema, artifact, and output validation—not a larger classifier.

## Common Pitfalls

### Pitfall 1: The present generator cannot exercise valid short-window criteria

**What goes wrong:** Monthly labs and weekly IoT make a “fresh” 24-hour prediction/rule test either stale or deceptively permissive. `[VERIFIED: backend/app/synthetic_data.py:268-277]` `lab_time = basis - timedelta(days=30 * (6 - month))`; `[VERIFIED: backend/app/synthetic_data.py:286-298]` `observed_at = basis - timedelta(days=7 * (8 - week))`.

**How to avoid:** Add deterministic daily terminal scenarios and explicit cutoff fixtures before the route; test exact 48-hour, seven-day, 24-hour freshness, and just-outside boundaries. [ASSUMED]

### Pitfall 2: Label-time leakage masquerades as accuracy

**What goes wrong:** A feature row includes an observation at or after the target event, a scenario/ID field, the future label, or the current rule output.

**How to avoid:** Represent cutoff as a required UTC argument; filter each source `<= cutoff`; make the label only from the open future interval; reject all forbidden columns before transformation; record the frame column list/checksum in the artifact manifest. [ASSUMED]

### Pitfall 3: SHAP is compared to a probability in the wrong space

**What goes wrong:** Binary XGBoost with `TreeExplainer(model_output="raw")` produces a raw margin/log-odds, not `predict_proba` output.

**How to avoid:** Use transformed columns in exactly the fitted order; run `check_additivity=True`; compare `expected_value + shap_sum` with XGBoost raw margin for the same frame/order, using the locked `1e-6` tolerance. [CITED: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html] [VERIFIED: 03-AI-SPEC.md:253-259] `model_output="raw"`, `check_additivity=True`, and `atol=1e-6`.

### Pitfall 4: Compatible-looking artifact, incompatible pipeline

**What goes wrong:** A joblib file passes an existence check but was made with different sklearn/dependency versions or a changed feature schema.

**How to avoid:** Verify checksum and complete manifest before load, turn `InconsistentVersionWarning` into an unavailable result, and train a new artifact after intended dependency upgrades. [CITED: https://scikit-learn.org/stable/model_persistence.html]

### Pitfall 5: Transaction retry repeats model work or mutates state

**What goes wrong:** Firestore may rerun a transaction callback after contention.

**How to avoid:** Compute/validate before a write batch; reserve the existing pointer transaction for pointer publication only. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions]

## Code Examples

### Cutoff gate before model work

```python
def build_prediction_frame(*, cutoff, ehr_events, iot_observations, schema):
    require_utc(cutoff)
    ehr = [event for event in ehr_events if event.event_time <= cutoff]
    iot = [item for item in iot_observations if item.observed_at <= cutoff]
    validate_provenance_and_units(ehr, iot)
    validate_freshness(ehr, iot, cutoff, schema.freshness_policy)
    raw = derive_allowlisted_features(ehr=ehr, iot=iot, cutoff=cutoff)
    if list(raw) != schema.raw_feature_columns:
        raise PredictionUnavailable("feature_schema_mismatch")
    return raw
```

This is a structural pattern: production code must retain each rejected reason and persist the locked unavailable response rather than raise a numeric fallback. [ASSUMED]

### SHAP validation in raw-margin space

```python
explainer = shap.TreeExplainer(classifier, model_output="raw")
values = explainer.shap_values(transformed, check_additivity=True)
raw_margin = classifier.predict(transformed, output_margin=True)[0]
assert isclose(explainer.expected_value + values[0].sum(), raw_margin, abs_tol=1e-6)
```

Use the same transformed columns and order for the classifier and explanation. [CITED: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Treat pickle/joblib as a portable model file | Trust-controlled bundle with environment/version metadata and checksum verification | Current sklearn guidance | A file is executable-code-adjacent input, not merely data. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Save generic XGBoost snapshots | Use model JSON/UBJSON for stable Booster representation when applicable | Current XGBoost guidance | JSON/UBJSON retains feature names, but the sklearn preprocessing contract still needs its own verified bundle member. [CITED: https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A daily terminal synthetic scenario series is the smallest safe extension to support valid rule and prediction tests. | Summary / Patterns | Generator changes could require adjustment if scenario volume is insufficient. |
| A2 | 24 hours is the initial required-observation freshness threshold. | Patterns | Valid predictions may be unnecessarily unavailable, or a different stream contract may warrant another policy. |
| A3 | `clinical_rules` and `aki_predictions` are suitable result subcollection IDs. | Diagram | Renaming later would require a Firestore migration. |
| A4 | RESOLVED: the Phase-3 artifact uses a versioned combined-stream allowlist with `latest_systolic_bp_mmhg`; Phase 6 still owns the formal EHR-only-versus-combined comparison. | Feature construction | Any later feature change requires a new schema and artifact version. |
| A5 | RESOLVED: SUS verdicts remain conservative registry-metadata signals; the user pre-authorized the named official packages subject to official identity, exact-version, and provenance verification. | Package audit | Failed official provenance or compatibility verification blocks installation/use. |

## Open Questions — RESOLVED

1. **RESOLVED — Baseline-creatinine review and limitation wording gate**
   - Clinical reviewer sign-off is unavailable during this autonomous prototype run. Phase 3 therefore gates release on automated source traceability, exact-boundary rule fixtures, creatinine-only wording assertions, and the immutable contract manifest rather than a fabricated approval.
   - A qualified nephrologist review remains explicitly required before any clinical use, downstream clinical-validation claim, or representation that the rule wording has clinical approval. The planning artifacts record that review as outstanding rather than blocking the autonomous Phase 3 implementation.

2. **RESOLVED — Phase 3 IoT-bearing inference scope**
   - Phase 3 combined-stream inference must include at least one meaningful IoT-derived feature because PRED-01 requires both the longitudinal EHR history and separate simulated IoT stream. The adopted schema adds cutoff-safe `latest_systolic_bp_mmhg` to the reviewed raw allowlist.
   - Phase 6 still owns the formal patient-held-out EHR-only-versus-combined comparison, comparative metrics, and report. Including one IoT-derived feature in the Phase 3 production artifact does not move that evaluation into this phase.

3. **RESOLVED — Named ML package authorization**
   - The user pre-authorized the official `pandas`, `scikit-learn`, `xgboost`, and `shap` packages at the named pins, so the conservative `SUS` registry result does not require an interactive checkpoint.
   - Before installation/use, execution must verify official package identity, exact version, and provenance, record the official project/source links and resolved versions, run `pip check`, and stop if those checks fail. Authorization does not relax the controlled-artifact checksum barrier.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Backend Python | model/training/tests | ✓ | Python 3.12.10; project requires `>=3.12`. `[VERIFIED: backend/pyproject.toml:5-14]` `requires-python = ">=3.12"`. | — |
| FastAPI/Pydantic | DTOs/routes | ✓ | local probe: FastAPI 0.142.2, Pydantic 2.13.5 | — |
| pytest | validation | ✓ | local probe: 8.4.2 | — |
| Firestore Python import | repository/live persistence | ✓ | 2026-10-04 local import probe succeeded | fakes remain the automated path |
| pandas/sklearn/XGBoost/SHAP | training/inference/attribution | ✗ | imports fail because not installed | install the user-authorized pins only after official identity/version/provenance verification |
| firebase/gcloud/Docker CLI | optional emulator/container proof | ✗ | commands not found | fake repository tests plus existing approved-runtime Firestore procedure |

**Missing dependencies with no fallback:** the ML stack is required before any valid XGBoost/SHAP inference can run.  
**Missing dependencies with fallback:** no Firebase emulator CLI is required for deterministic fake-client tests.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 (local probe) |
| Config file | `[VERIFIED: backend/pyproject.toml:23-25]` `testpaths = ["tests"]` and `addopts = "-q"` |
| Quick run command | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_clinical_rules.py backend/tests/test_aki_features.py -q` |
| Full suite command | `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRED-01 | Strict post-cutoff 24-hour synthetic label and valid score | pure unit + model fixture | `pytest tests/test_aki_features.py tests/test_aki_model.py -q` | ❌ Wave 0 |
| PRED-02 | Missing/type/unit/stale/future/schema/artifact input never reaches model | parameterized unit | `pytest tests/test_aki_features.py tests/test_aki_model.py -q` | ❌ Wave 0 |
| PRED-03 | Unavailable has reasons and no probability/attributions | Pydantic + route contract | `pytest tests/test_prediction_routes.py -q` | ❌ Wave 0 |
| PRED-04 | Separate types/paths; batch failure writes neither result nor active pointer | fake-Firestore integration | `pytest tests/test_patients.py tests/test_prediction_routes.py -q` | ❌ Wave 0 |
| PRED-05 | SHAP names/order and raw-margin additivity match valid model; failure becomes unavailable | model unit | `pytest tests/test_aki_model.py -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** focused pytest file(s) for the module changed.
- **Per wave merge:** `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`.
- **Phase gate:** run the AI-SPEC reference scenario command and verify its immutable manifest once the script and 24+ fixtures exist.

### Wave 0 Gaps

- [ ] `backend/tests/test_clinical_rules.py` — KDIGO boundary/window/unit/evidence/limitation fixtures.
- [ ] `backend/tests/test_aki_features.py` — cutoff, freshness, provenance, forbidden column, and label boundaries.
- [ ] `backend/tests/test_aki_model.py` — trusted artifact, checksum/version mismatch, deterministic output, SHAP alignment/additivity.
- [ ] `backend/tests/test_prediction_routes.py` — authorization, union shape, result separation, and fake-Firestore batch failure.
- [ ] `backend/tests/fixtures/aki_reference_scenarios.json` — independently authored 24+ deterministic scenarios from the AI-SPEC.
- [ ] `backend/scripts/evaluate_phase3_contract.py` and `backend/scripts/verify_eval_manifest.py` — required contract-manifest gate.
- [ ] Official identity, exact-version, provenance, and resolver compatibility verification for all four user-authorized packages before dependency modification.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing Firebase token verification remains a route dependency. `[VERIFIED: backend/app/patient_routes.py:18-24]` `Depends(require_doctor)`. |
| V3 Session Management | yes | Bearer-token security behavior stays in the existing server boundary; no new session storage. [VERIFIED: 03-CONTEXT.md] |
| V4 Access Control | yes | Exact doctor-only authorization precedes result repository access. `[VERIFIED: backend/app/patient_routes.py:18-24]` `Depends(require_doctor)` then `Depends(get_patient_repository)`. |
| V5 Input Validation | yes | Pydantic discriminated response union; strict path/cutoff/unit/provenance/schema/freshness validation before model load. [VERIFIED: 03-AI-SPEC.md:301-330] |
| V6 Cryptography | yes | SHA-256 bundle verification detects controlled-store tampering but does not make untrusted pickle safe; credentials stay backend-only. [CITED: https://scikit-learn.org/stable/model_persistence.html] |

### Known Threat Patterns for the Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted serialized artifact executes code | Tampering / Elevation of privilege | Request-independent controlled location, checksum/manifest verification before load, and no untrusted artifact deserialization. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Future/label/ID/rule field reaches feature matrix | Tampering | Explicit cutoff and deny-list/allowlist validation before transformer execution. [VERIFIED: 03-CONTEXT.md] |
| Unavailable is rendered/stored as numeric zero | Integrity | Discriminated DTOs; unavailable forbids probability/attributions; route/repository contract tests. [VERIFIED: 03-AI-SPEC.md:301-326] |
| Cross-type or partial Firestore write | Integrity | One validated write batch for two distinct immutable result documents; no active-pointer mutation. [CITED: https://firebase.google.com/docs/firestore/manage-data/transactions] |
| Browser or non-doctor calls inference/read route | Spoofing / Elevation of privilege | Reuse exact `require_doctor` dependency and server-only repository factory. `[VERIFIED: backend/app/patient_routes.py:13-24]` `return PatientRepository.from_firestore()` and `Depends(require_doctor)`. |

## Sources

### Primary (official documentation consulted)

- [KDIGO 2012 AKI Guideline](https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf) — creatinine and urine-output definition/staging.
- [scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html) — pickle/joblib trust, version compatibility, and metadata limits.
- [scikit-learn composite estimators](https://scikit-learn.org/stable/modules/compose.html) — pipeline/column transformer behavior.
- [XGBoost model IO](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html) and [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) — stable model formats and feature-name persistence.
- [SHAP TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html) — raw margins, feature ordering, and additivity checks.
- [Firestore transactions and batched writes](https://firebase.google.com/docs/firestore/manage-data/transactions) and [quotas](https://firebase.google.com/docs/firestore/quotas) — atomicity, retry behavior, and request limit.

### Secondary (MEDIUM confidence)

- Official sources were fetched through WebSearch because Context7 was unavailable to this agent; the confidence seam classified cross-checked WebSearch evidence as MEDIUM.

## Metadata

**Confidence breakdown:**

- Standard stack: MEDIUM — official docs and registry version queries were checked; the user authorized the named official packages, but execution must still record official identity/version/provenance and complete resolver compatibility because the conservative legitimacy seam marked the candidates SUS and the dry-run timed out.
- Architecture: HIGH — locked phase contract plus opened Phase-2 repository/source boundaries; proposed names and threshold remain explicitly assumed.
- Pitfalls: MEDIUM — official KDIGO/scikit/XGBoost/SHAP/Firestore documentation confirms the critical mechanics; generator-extension design is assumed.

**Research date:** 2026-10-04  
**Valid until:** 2026-10-11 (fast-moving package compatibility); automated Phase 3 contracts remain executable, while qualified nephrologist review stays outstanding and required before clinical use or any clinical-validation claim.
