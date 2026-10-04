---
phase: 03-clinical-rules-and-aki-prediction
plan: "02"
subsystem: backend clinical rules and synthetic data
tags: [python, pytest, synthetic-data, kdigo, aki]
requires:
  - Phase 03 Plan 01 separate clinical-result contracts and active immutable cohort patterns
provides:
  - Deterministic terminal synthetic evidence for explicit cutoff-safe label construction
  - Auditable, creatinine-only KDIGO 2012 current-rule results with safe insufficient-evidence handling
affects: [phase-03-03-training, phase-03-05-inference, phase-04-dashboard, phase-05-patient-detail]
tech-stack:
  added: []
  patterns: [cutoff-relative deterministic terminal evidence, fixture-authored KDIGO boundary tests, explicit selected-evidence audit trail]
key-files:
  created:
    - backend/tests/test_clinical_rules.py
    - backend/tests/fixtures/aki_reference_scenarios.json
  modified:
    - backend/app/synthetic_data.py
    - backend/app/clinical_rules.py
    - backend/tests/test_synthetic_data.py
decisions:
  - Terminal evidence uses time_basis minus 24 hours as the explicit cutoff, preserving time_basis as the inclusive record upper bound.
  - The current-rule result records only evaluated creatinine criteria and fails closed as insufficient when no reproducible comparator exists.
  - A criteria_not_met result means no supported creatinine criterion was met and never asserts a complete no-AKI conclusion.
requirements-completed: [PRED-01, PRED-04]
coverage:
  - id: D1
    description: Deterministic synthetic terminal creatinine and cutoff-aligned blood-pressure observations support derived next-24-hour labels without persisted outcomes.
    requirement: PRED-01
    verification:
      - kind: unit
        ref: backend/tests/test_synthetic_data.py#test_terminal_trajectories_derive_both_label_classes_without_persisted_labels
        status: pass
    human_judgment: false
  - id: D2
    description: Creatinine-only KDIGO boundary evaluation records selected evidence, baseline, source/version, and limitation wording.
    requirement: PRED-04
    verification:
      - kind: unit
        ref: backend/tests/test_clinical_rules.py#test_reference_scenarios_match_independently_authored_expected_outcomes
        status: pass
    human_judgment: true
    rationale: A nephrologist must review the baseline method and creatinine-only limitation wording before any clinical use or clinical-validation claim.
metrics:
  duration: 5m
  completed: 2026-10-04
  tasks_completed: 2
commits: 5
plan_head_before: c16315be8a2105a64bbbf0e833a0cb2ca2bf970a
plan_head_after: 9997c586d868c62adfb1769fef7a39f1af8432ab
actuals:
  tokens: 5647
  tasks: 2
  commits: 5
status: complete
---

# Phase 03 Plan 02: Clinical Rules and AKI Prediction Summary

Deterministic synthetic terminal evidence now supports explicit cutoff-safe trajectories, while KDIGO 2012 serum-creatinine checks return separately auditable current-rule results rather than future-risk claims.

## Completed Tasks

1. Added deterministic daily terminal creatinine observations from seven days before cutoff through the following 24 hours, plus a cutoff-aligned simulated blood-pressure observation. Stable and worsening trajectories remain ordinary, provenance-complete clinical records with no outcome labels.
2. Completed the creatinine-only KDIGO rule path with exact 48-hour and seven-day boundaries, selected evidence/baseline audit fields, invalid-input fail-closed behavior, and ten independently authored reference cases.

## Verification

- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_synthetic_data.py backend/tests/test_patients.py -q` — passed (22 tests).
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/test_clinical_rules.py backend/tests/test_synthetic_data.py -q` — passed (19 tests).
- `backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -q` — passed (61 tests).
- `git diff --check` — passed.

## Task Commits

1. Task 1 RED — `5b948c6` `test(03-02): add failing terminal trajectory tests`
2. Task 1 GREEN — `6df4b64` `feat(03-02): add deterministic terminal clinical evidence`
3. Task 2 RED — `49bcce6` `test(03-02): add KDIGO creatinine rule reference cases`
4. Task 2 GREEN — `35da5b5` `feat(03-02): audit creatinine-only KDIGO rule results`
5. Task 2 REFACTOR — `9997c58` `refactor(03-02): type clinical evidence selection`

## Decisions Made

- Use `time_basis - 24h` as an explicit cutoff so the post-cutoff terminal outcome remains within the cohort's pre-existing inclusive upper time bound.
- Persist a supported negative only for the creatinine criteria that could actually be evaluated; preserve the explicit urine-output limitation.
- Keep source, rule version, baseline method/value, selected evidence, and evaluated/met criteria in every result so later persistence and UI layers can show the assessment basis.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 1 - Bug] Filtered non-creatinine events before sorting rule evidence.
- **Found during:** Task 1 RED verification.
- **Issue:** The existing rule path sorted `None` values returned for non-creatinine EHR events, raising before it could calculate a status from a normal full history.
- **Fix:** Filtered to parsed creatinine evidence before ordering it.
- **Files modified:** `backend/app/clinical_rules.py`
- **Verification:** Synthetic terminal trajectory and full backend suites pass.
- **Committed in:** `6df4b64`

**Total deviations:** 1 auto-fixed (Rule 1).

## Clinical Review Status

The independently authored reference fixture records `nephrologist review pending`. Automated verification passed, but a nephrologist must review the selected baseline method and creatinine-only limitation wording before any clinical use or clinical-validation claim. This is not represented as approval.

## TDD Gate Compliance

- Task 1 RED: `5b948c6` failed intentionally because terminal cutoff-safe observations did not yet exist; GREEN: `6df4b64` passed the focused regression suite.
- Task 2 RED: `49bcce6` failed intentionally on fixture-backed missing audit fields and insufficient-evidence boundaries; GREEN: `35da5b5` passed all reference scenarios; REFACTOR: `9997c58` preserved the focused suite.

## Known Stubs

None.

## Next Phase Readiness

Training and inference work can derive labels from ordinary cutoff-safe evidence while excluding scenario metadata, patient IDs, rule outputs, and future observations from candidate feature values.

## Self-Check: PASSED

- Required implementation, fixture, test, and summary files exist.
- Task commits `5b948c6`, `6df4b64`, `49bcce6`, `35da5b5`, and `9997c58` exist in git history.
