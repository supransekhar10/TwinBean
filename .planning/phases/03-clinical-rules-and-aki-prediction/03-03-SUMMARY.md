---
phase: 03-clinical-rules-and-aki-prediction
plan: "03"
subsystem: backend-ml-feature-contract
tags: [python, pandas, xgboost, shap, aki, feature-validation]
requires:
  - 03-01 clinical result boundary and active cohort context
provides:
  - Exact user-authorized ML dependency provenance
  - Cutoff-safe combined EHR/IoT feature snapshots
  - Strict new-AKI-within-24-hours training labels
affects:
  - Phase 03 model artifact and inference plans
  - Phase 06 held-out evaluation
tech_stack:
  added: [pandas==3.0.6, scikit-learn==1.9.1, xgboost==3.4.1, shap==0.52.0]
  patterns: [immutable feature schema, fail-closed preflight, timestamp-safe training labels]
key_files:
  created: [docs/ML_DEPENDENCIES.md, backend/app/aki_features.py, backend/tests/test_aki_features.py]
  modified: [backend/pyproject.toml]
decisions:
  - "Feature rows contain only the reviewed four-column combined-stream allowlist; grouping and labels remain outside X."
  - "Any malformed, future, stale, non-UTC, provenance-invalid, or ownership-invalid request input returns a stable unavailable reason before pandas/model work."
  - "Training assigns label 1 only for a supported new AKI event in (cutoff, cutoff + 24h], never for AKI already supported at cutoff."
metrics:
  duration: "31m"
  completed: "2026-10-04"
status: complete
actuals:
  tokens: 4968
  tasks: 2
  commits: 3
commits: 3
plan_head_before: 0c4f4af6325c2bc32507c5535819ef8c1161181a
plan_head_after: fc39e18c66f20b8ebbc112cc683715f45d9d0572
---

# Phase 03 Plan 03: ML Dependencies and Cutoff-Safe Feature Contract Summary

TwinBean now has a pinned, provenance-recorded local ML stack and a pure fail-closed contract that builds one ordered EHR/IoT feature row only from validated synthetic evidence at an explicit UTC cutoff.

## Completed Tasks

1. Pinned the user-authorized pandas, scikit-learn, XGBoost, and SHAP releases; installed the editable backend; verified import metadata equality and `pip check`; and documented official provenance and compatibility-upgrade policy.
2. Added the versioned feature/freshness/label contracts, stable unavailable reasons, exact four-column pandas frame, and strict new-AKI label generation with RED then GREEN tests.

## Verification

- `backend\\.venv\\Scripts\\python.exe -c "... importlib.metadata ... pip check ..."` — passed: pandas 3.0.6, scikit-learn 1.9.1, xgboost 3.4.1, and shap 0.52.0; no broken requirements.
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_aki_features.py -q` — passed, 11 tests.
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q` — passed, 72 tests.

## TDD Gate Compliance

- RED: `c5bf180` added the contract tests; the focused suite failed on the intentional `snapshot.status == "available"` assertion before implementation.
- GREEN: `fc39e18` implemented the feature and label contract; all focused tests passed.
- REFACTOR: no separate cleanup commit was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical validation] Validated future training creatinine evidence before label calculation**
- **Found during:** Task 2
- **Issue:** Training labels read future-window creatinine events, so only validating pre-cutoff feature evidence would allow malformed future outcome inputs into the label path.
- **Fix:** Applied the same creatinine schema, unit, numeric, and leakage-field validation to every training creatinine event before deriving a label.
- **Files modified:** `backend/app/aki_features.py`
- **Commit:** `fc39e18`

## Known Stubs

None.

## Self-Check: PASSED

- Confirmed all four planned implementation files exist.
- Confirmed task commits `a37c703`, `c5bf180`, and `fc39e18` exist in git history.
