---
phase: 03-clinical-rules-and-aki-prediction
plan: "04"
subsystem: backend ML artifact release and explanation integrity
tags: [python, scikit-learn, xgboost, shap, joblib, artifact-verification]
requires:
  - phase: 03-02
    provides: deterministic terminal synthetic evidence and cutoff-safe labels
  - phase: 03-03
    provides: pinned ML dependencies and four-column feature contract
provides:
  - deterministic patient-disjoint synthetic XGBoost release bundle
  - checksum, package, schema, cohort, and partition verification before joblib deserialization
  - fail-closed raw-margin SHAP explanation integrity gate
affects: [03-05 inference integration, phase-06 evaluation, phase-04 dashboard, phase-05 patient detail]
tech-stack:
  added: []
  patterns: [controlled artifact store, manifest-before-deserialization, raw-margin SHAP reconciliation]
key-files:
  created:
    - backend/app/aki_model.py
    - backend/app/aki_explanations.py
    - backend/scripts/train_aki_model.py
    - backend/tests/test_aki_model.py
    - backend/model_artifacts/aki-24h-2026.10.04/manifest.json
    - backend/model_artifacts/aki-24h-2026.10.04/feature-schema.json
    - backend/model_artifacts/aki-24h-2026.10.04/pipeline.joblib
  modified: []
key-decisions:
  - "Release loading is restricted to one configured direct-child artifact directory and verifies every trust claim before joblib.load."
  - "SHAP explanations use the exact transformed feature names and reconcile in raw-margin space with zero relative tolerance and 1e-6 absolute tolerance."
patterns-established:
  - "A numeric prediction is only usable by later service code when the matching explanation integrity gate succeeds."
  - "Release manifests retain only group/cohort digests, never patient IDs, and label the bundle synthetic research use only."
requirements-completed: [PRED-01, PRED-02, PRED-05]
coverage:
  - id: D1
    description: "Deterministic synthetic XGBoost release bundle rejects untrusted, incomplete, tampered, incompatible, and request-selected artifacts before deserialization."
    requirement: PRED-02
    verification:
      - kind: unit
        ref: "backend/tests/test_aki_model.py#test_loader_rejects_untrusted_or_tampered_members_before_deserialization"
        status: pass
      - kind: other
        ref: "backend/.venv/Scripts/python.exe -m pytest backend/tests -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "Verified synthetic new-AKI probability and raw-margin SHAP values are deterministic, aligned, finite, and fail closed on explanation faults."
    requirement: PRED-05
    verification:
      - kind: unit
        ref: "backend/tests/test_aki_model.py#test_explanation_uses_exact_transformed_feature_order_and_raw_margin_additivity"
        status: pass
      - kind: unit
        ref: "backend/tests/test_aki_model.py#test_explanation_rejects_name_mismatch_additivity_failure_and_shap_exception"
        status: pass
    human_judgment: false
metrics:
  duration: 37m
  completed: 2026-10-04
  tasks_completed: 2
commits: 4
plan_head_before: 3b6c99e4a56d4bbcb54f516197acdf515bbb7b07
plan_head_after: 2442d10da1d0a85ac0fb7465a0c29b2cb5096ba0
actuals:
  tokens: 63961
  tasks: 2
  commits: 4
status: complete
---

# Phase 03 Plan 04: Verified AKI Model Release Summary

Deterministic synthetic XGBoost inference now ships as a controlled checksum-verified bundle with raw-margin SHAP values that fail closed on any alignment or additivity fault.

## Completed Tasks

1. Added the fixed four-feature sklearn/XGBoost pipeline, explicit seeded training command, patient-disjoint development partition, immutable synthetic-research manifest, and loader that rejects trust-boundary failures before `joblib.load`.
2. Published `aki-24h-2026.10.04`, then added SHAP TreeExplainer checks for transformed/booster name order, finite attributions, raw-margin additivity, and typed explanation-integrity failures.

## Verification

- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_aki_model.py -q -k "pipeline or artifact or probability"` — passed (2 selected tests).
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_aki_model.py -q` — passed (7 tests).
- Reload canary through `load_verified_bundle` — passed: probability `0.461789816618`, 4 attributions, repeated probability tolerance `<=1e-12`, and repeated attribution tolerance `<=1e-6`.
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q` — passed (79 tests).
- `git diff --check` — passed.

## Task Commits

1. Task 1 RED — `27d709f` `test(03-04): add failing model artifact contract`
2. Task 1 GREEN — `7021e73` `feat(03-04): release verified AKI model bundle`
3. Task 2 RED — `17a511f` `test(03-04): add failing SHAP integrity contract`
4. Task 2 GREEN — `2442d10` `feat(03-04): validate raw-margin SHAP explanations`

## Decisions Made

- Restrict release loading to a configured direct child of the backend-controlled artifact root; request data cannot select an artifact path.
- Represent explanation integrity as a typed failure so Plan 03-05 can make the complete forecast unavailable rather than leave a numeric score available.
- Keep the bundle explicitly synthetic research only and omit clinical thresholds, AUROC, calibration, or held-out performance claims.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 2 - Missing critical validation] Validated nested cohort and partition manifest metadata before deserialization.
- **Found during:** Task 1 trust-barrier tests.
- **Issue:** A manifest with a missing cohort snapshot checksum or a non-digest partition field could otherwise pass top-level validation and reach `joblib.load`.
- **Fix:** Enforced complete cohort fields, SHA-256-only snapshot and partition digests, UTC time metadata, and positive held-out count before deserialization.
- **Files modified:** `backend/app/aki_model.py`, `backend/tests/test_aki_model.py`
- **Verification:** Tamper tests prove `joblib.load` is not invoked for every tested mismatch.
- **Committed in:** `7021e73`

**Total deviations:** 1 auto-fixed (Rule 2).

## TDD Gate Compliance

- Task 1 RED: `27d709f` intentionally failed because `make_aki_pipeline` was absent; a persisted RED-evidence record was accepted before GREEN work.
- Task 1 GREEN: `7021e73` passed the focused artifact/probability suite and all model tests.
- Task 2 RED: `17a511f` intentionally failed because `explain_prediction` was absent; a persisted RED-evidence record was accepted before GREEN work.
- Task 2 GREEN: `2442d10` passed feature-alignment, non-finite, additivity, exception, and full backend checks.
- REFACTOR: no separate cleanup was needed.

## Known Stubs

None.

## Next Phase Readiness

Plan 03-05 can load the static controlled bundle, call prediction and explanation as one fail-closed operation, and map either typed integrity error to an unavailable forecast. The release contains no clinical-validation or performance claim.

## Self-Check: PASSED

- Required source, training, test, release bundle, and schema files exist.
- Task commits `27d709f`, `7021e73`, `17a511f`, and `2442d10` exist in git history.
- The focused model suite and full backend suite pass after the independent reload canary.
