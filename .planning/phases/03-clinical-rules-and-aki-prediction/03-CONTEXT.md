# Phase 3: Clinical Rules and AKI Prediction - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning
**Mode:** Autonomous recommendations accepted from the user's overnight brief

<domain>
## Phase Boundary

Deliver the backend clinical-calculation and inference layer for synthetic adult CKD records: source-backed current AKI rule results, XGBoost-based new-AKI-within-24-hours predictions, explicit unavailable states, prediction timestamps, data-quality warnings, and SHAP attributions. Store and return clinical rules and future predictions as distinct versioned result types. Dashboard and patient-detail presentation remain in Phases 4 and 5; comparative held-out evaluation remains in Phase 6.

</domain>

<decisions>
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/synthetic_data.py` provides deterministic adult CKD histories and a separate simulated IoT stream with UTC timestamps and exact provenance.
- `backend/app/patients.py` provides immutable versioned cohort staging, checksum validation, active-pointer reads, strict provenance checks, and separate EHR/IoT response models.
- `backend/app/auth.py` and `backend/app/patient_routes.py` provide the established exact-doctor authorization and dependency-injected repository pattern.

### Established Patterns
- Pydantic response models, lazy Firebase Admin imports, explicit CLI entry points, deterministic IDs, bounded Firestore operations, and failure-first tests.
- Credentials and tokens remain backend-only; evidence artifacts record sanitized facts only.
- Bounded implement/check/fix cycle with no test weakening and at most three failed attempts per blocker.

### Integration Points
- Add clinical calculation, feature construction, model artifact, inference, and explanation modules under `backend/app`.
- Extend synthetic generation/training tooling under `backend/scripts` without introducing startup side effects.
- Extend the active cohort repository and protected patient routes with distinct rule and prediction contracts.
- Add model dependencies to `backend/pyproject.toml` with compatible bounded versions and document reproducible installation/training commands.

</code_context>

<specifics>
## Specific Ideas

- Synthetic evaluation and inference outputs must always be labelled research/synthetic, never clinical validation.
- SHAP values describe model influence only and must not be presented as causal effects.
- “Risk unavailable” is a first-class state, not a display-only transformation.
- Actual baseline comparison, held-out metrics, event prevalence, patient-level splits, and EHR-only versus combined evaluation are required later in Phase 6.

</specifics>

<deferred>
## Deferred Ideas

- Doctor dashboard ranking and summary states: Phase 4.
- Patient detail charts, replay controls, and separate visual sections: Phase 5.
- Final comparative evaluation report and metrics: Phase 6.
- Optional AI copilot: outside the core prediction path and not required for this milestone.

</deferred>
