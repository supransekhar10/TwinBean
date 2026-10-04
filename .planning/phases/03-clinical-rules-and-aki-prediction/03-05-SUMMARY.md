---
phase: 03-clinical-rules-and-aki-prediction
plan: "05"
subsystem: backend clinical inference and Firestore results
tags: [fastapi, anyio, xgboost, shap, firestore, pydantic]
requires:
  - phase: 03-01
    provides: separate clinical rule and prediction contracts with protected generation
  - phase: 03-04
    provides: checksum-verified XGBoost release bundle and fail-closed SHAP explanations
provides:
  - Server-selected available 24-hour AKI inference with validated SHAP attributions
  - Explicit unavailable forecasts for preflight, artifact, model, and explanation failures
  - Atomic separate Firestore rule and prediction persistence with bounded protected reads
affects: [phase-04-dashboard, phase-05-patient-detail, phase-06-evaluation]
actuals:
  tokens: 6499
  tasks: 2
  commits: 2
commits: 2
plan_head_before: a9557bc5edde2f2cd6205589cfdd9f9e4ea6631c
plan_head_after: ef441327a9fd1a898bd69fc8eda7c7ae95c6ff59
tech-stack:
  added: []
  patterns: [server-controlled artifact selection, bounded worker-thread inference, atomic paired result writes, distinct typed result histories]
key-files:
  created: []
  modified:
    - backend/.env.example
    - backend/app/settings.py
    - backend/app/prediction_service.py
    - backend/app/patients.py
    - backend/app/patient_routes.py
    - backend/tests/test_prediction_routes.py
    - backend/tests/test_patients.py
key-decisions:
  - "Only immutable server settings select the direct-child model release and positive inference concurrency limit; requests cannot choose either."
  - "An available probability is returned only after both verified model scoring and raw-margin SHAP validation succeed."
  - "Rule and prediction histories remain separate typed endpoints and Firestore subcollections under the exact active synthetic cohort owner."
patterns-established:
  - "Expected feature, artifact, model, and explanation failures convert to reason-coded unavailable predictions with no numeric fallback."
  - "Paired result DTOs are validated before one two-document Firestore batch and reads revalidate active-cohort provenance."
requirements-completed: [PRED-01, PRED-02, PRED-03, PRED-04, PRED-05]
coverage:
  - id: D1
    description: "Valid active synthetic contexts produce a complete released-bundle XGBoost probability with prediction metadata and non-empty SHAP attributions beside the independent current rule."
    requirement: PRED-02
    verification:
      - kind: integration
        ref: "backend/tests/test_prediction_routes.py#test_verified_engine_returns_a_complete_released_bundle_forecast"
        status: pass
    human_judgment: false
  - id: D2
    description: "Invalid feature inputs and artifact/model/SHAP failures remain explicit unavailable predictions without probability or attribution fallback."
    requirement: PRED-03
    verification:
      - kind: unit
        ref: "backend/.venv/Scripts/python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_aki_features.py backend/tests/test_aki_model.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "Rule and prediction documents persist atomically under separate active-cohort paths and return through separate bounded exact-doctor endpoints."
    requirement: PRED-04
    verification:
      - kind: integration
        ref: "backend/tests/test_patients.py#test_clinical_result_histories_are_distinct_bounded_and_newest_first"
        status: pass
      - kind: integration
        ref: "backend/tests/test_prediction_routes.py#test_denied_result_history_reads_never_invoke_the_repository"
        status: pass
    human_judgment: false
metrics:
  duration: 3h48m
  completed: 2026-10-04
  tasks_completed: 2
status: complete
---

# Phase 03 Plan 05: Verified AKI Inference and Clinical Result Histories Summary

Server-controlled XGBoost inference now returns an available forecast only with a valid cutoff-safe snapshot and reconciled SHAP explanation, while atomically preserving separate observed-rule and future-risk records.

## Performance

- **Duration:** 3h48m
- **Started:** 2026-10-04T19:34:49+05:30
- **Completed:** 2026-10-04T23:22:36+05:30
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Replaced the tracer default with the checksum-verified released XGBoost/SHAP engine, including complete version, freshness, cutoff, generation-time, warning, and attribution fields.
- Preserved explicit reason-coded unavailable results for every preflight or verified inference failure without ever substituting probability zero.
- Offloaded synchronous model/SHAP generation through a configured positive AnyIO capacity limiter after exact-doctor authorization.
- Validated and atomically persisted paired rule/prediction DTOs under distinct active-cohort subcollections, then exposed bounded newest-first typed histories through separate doctor-only routes.

## Task Commits

1. **Task 1: Wire valid XGBoost plus SHAP inference through the protected route** - `2e78139`
2. **Task 2: Complete atomic writes and separate bounded result reads** - `ef44132`

## Verification

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_aki_features.py backend/tests/test_aki_model.py -q` - passed (26 tests).
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_patients.py -q` - passed (26 tests).
- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp backend\tests\.tmp-03-05-full-elevated` - passed (84 tests).
- `git diff --check` - passed.

## Decisions Made

- Configuration accepts only a direct release name and resolves it beneath the backend-controlled artifact root; request bodies never select artifact paths or concurrency.
- Artifact/model integrity errors share a sanitized unavailable reason, while SHAP integrity failures use a distinct sanitized reason; neither path retains a probability.
- Stored result reads validate active cohort, patient ownership, result type, and synthetic provenance before parsing the distinct response DTO.

## Deviations from Plan

None - plan functionality was implemented within the specified files and trust boundaries.

## Issues Encountered

- Windows restricted-token ACLs prevented pytest from using both its default temporary directory and sandbox-created base directories. The unchanged full suite passed outside the restricted token with an isolated workspace base directory.
- A prior test-side effect left the tracked model release directory inaccessible and its three files deleted. The exact directory was replaced and all tracked artifacts were restored from `HEAD`; the final full suite and status check confirmed the release bundle remained intact.

## TDD Gate Compliance

- Plan type is `execute` and project `workflow.tdd_mode` is disabled. Both task behavior additions were first observed failing against the tracer/missing-history endpoints, then passed after implementation; task-level tests and implementation were committed atomically as requested.

## Known Stubs

None.

## Self-Check: PASSED

- All seven planned implementation/test files exist.
- Task commits `2e78139` and `ef44132` exist in git history.
- The released `feature-schema.json`, `manifest.json`, and `pipeline.joblib` files are present and tracked.

## Next Phase Readiness

- Phase 04 can consume separate current-rule and future-risk result histories without conflating clinical concepts.
- Phase 06 can reuse the same verified bundle and feature contract for formal held-out evaluation; no clinical performance claim was introduced here.

---
*Phase: 03-clinical-rules-and-aki-prediction*
*Completed: 2026-10-04*
