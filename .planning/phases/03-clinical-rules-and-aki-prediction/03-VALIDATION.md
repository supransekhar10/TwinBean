---
phase: "03"
slug: "clinical-rules-and-aki-prediction"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-04"
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for continuous feedback during execution. This file is seeded by planning; `$gsd-validate-phase 03` promotes it from `draft` after reconciling executed test evidence.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 in the backend Python 3.12 virtual environment |
| **Config file** | `backend/pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-q"`) |
| **Quick run command** | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_clinical_rules.py backend/tests/test_aki_features.py -q` |
| **Full suite command** | `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` |
| **Release-gate command** | `.\backend\.venv\Scripts\python.exe -m scripts.evaluate_phase3_contract --reference backend/tests/fixtures/aki_reference_scenarios.json --output backend/artifacts/evals/phase3-contract.json --fail-on-rubric; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; .\backend\.venv\Scripts\python.exe -m scripts.verify_eval_manifest backend/artifacts/evals/phase3-contract.json; exit $LASTEXITCODE` |
| **Feedback target** | Focused task checks target less than 60 seconds; execution records actual timings and escalates slower commands without weakening coverage |

---

## Sampling Rate

- **After every task commit:** Run that task's exact focused command from the map below.
- **After every plan wave:** Run `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`.
- **After Wave 5 / before `$gsd-verify-work`:** Run the full suite, then generate a fresh contract manifest with `--fail-on-rubric`, then validate that generated manifest.
- **Max feedback latency:** Target less than 60 seconds for focused checks; record and investigate any slower command during execution.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Test Artifact Timing | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|----------------------|--------|
| 03-01-01 | 01 | 1 | PRED-03, PRED-04 | T-03-01, T-03-02, T-03-03 | Exact-doctor route returns separate rule/unavailable forecast and atomically writes distinct documents. | route + fake-Firestore integration | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py -q` | Created in task before verify | ⬜ pending |
| 03-01-02 | 01 | 1 | PRED-03, PRED-04 | T-03-01, T-03-02 | Authorization short-circuits, deterministic IDs repeat, and batch failure mutates no protected state. | route + repository integration | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_patients.py backend/tests/test_auth.py backend/tests/test_health.py -q` | Existing tests extended in task | ⬜ pending |
| 03-02-01 | 02 | 2 | PRED-01 | T-03-05 | Deterministic terminal EHR and IoT observations support cutoff-safe combined-stream rows and strict future labels. | deterministic unit + repository regression | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_synthetic_data.py backend/tests/test_patients.py -q` | Existing tests extended in task | ⬜ pending |
| 03-02-02 | 02 | 2 | PRED-04 | T-03-04 | KDIGO creatinine thresholds/windows preserve evidence and never imply urine-output assessment. | parameterized unit + reference fixture | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_clinical_rules.py backend/tests/test_synthetic_data.py -q` | Created in task before verify | ⬜ pending |
| 03-03-01 | 03 | 2 | PRED-02 | T-03-SC | Only pre-authorized official packages at exact pins pass identity/version/provenance and resolver checks. | dependency metadata + pip consistency | `backend\.venv\Scripts\python.exe -c "import subprocess,sys; from importlib.metadata import version; expected={'pandas':'3.0.6','scikit-learn':'1.9.1','xgboost':'3.4.1','shap':'0.52.0'}; assert {name:version(name) for name in expected} == expected; subprocess.run([sys.executable,'-m','pip','check'],check=True)"` | Uses environment updated in task | ⬜ pending |
| 03-03-02 | 03 | 2 | PRED-01, PRED-02, PRED-03 | T-03-06, T-03-07 | Cutoff/provenance/unit/freshness gates build only the four-column EHR+IoT allowlist or return a reason-coded unavailable state. | parameterized unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_aki_features.py -q` | Created in task before verify | ⬜ pending |
| 03-04-01 | 04 | 3 | PRED-01, PRED-02 | T-03-08, T-03-10 | Seeded combined-stream pipeline is reproducible and every bundle check passes before deserialization. | model + artifact unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_aki_model.py -q -k "pipeline or artifact or probability"` | Created in task before verify | ⬜ pending |
| 03-04-02 | 04 | 3 | PRED-05 | T-03-09 | SHAP names/order and raw-margin additivity match; any explanation failure invalidates the score. | model + explanation unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_aki_model.py -q` | Existing task test file extended | ⬜ pending |
| 03-05-01 | 05 | 4 | PRED-01, PRED-02, PRED-03, PRED-05 | T-03-11, T-03-12 | Protected async route uses both source streams and returns available only after artifact/model/SHAP validation. | route + feature + model integration | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_aki_features.py backend/tests/test_aki_model.py -q` | Existing task test files extended | ⬜ pending |
| 03-05-02 | 05 | 4 | PRED-03, PRED-04 | T-03-11, T-03-13 | Available/unavailable pairs commit atomically and separate doctor-only reads never cross result types. | route + fake-Firestore integration + regression | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_prediction_routes.py backend/tests/test_patients.py backend/tests -q` | Existing task test files extended | ⬜ pending |
| 03-06-01 | 06 | 5 | PRED-01 through PRED-05 | T-03-14 | The independently expected 24+ scenarios cover rule, combined-stream forecast, unavailable, auth, and atomicity rubrics; any critical failure is nonzero. | contract evaluator unit/integration | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase3_contract.py -q` | Created in task before verify | ⬜ pending |
| 03-06-02 | 06 | 5 | PRED-01 through PRED-05 | T-03-15, T-03-16 | A fresh evaluator run against the current artifact precedes manifest verification, preventing stale evidence from passing release. | full contract release gate | `.\backend\.venv\Scripts\python.exe -m scripts.evaluate_phase3_contract --reference backend/tests/fixtures/aki_reference_scenarios.json --output backend/artifacts/evals/phase3-contract.json --fail-on-rubric; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; .\backend\.venv\Scripts\python.exe -m scripts.verify_eval_manifest backend/artifacts/evals/phase3-contract.json; exit $LASTEXITCODE` | Evaluator, verifier, fixture, and artifact exist by task verify | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave Coverage

| Wave | Plans | Tasks with Automated Verify | Wave Exit Gate | Coverage |
|------|-------|-----------------------------|----------------|----------|
| 1 | 03-01 | 2 / 2 | Full backend pytest suite | Continuous |
| 2 | 03-02, 03-03 | 4 / 4 | Full backend pytest suite after both parallel plans complete | Continuous |
| 3 | 03-04 | 2 / 2 | Full backend pytest suite plus released-bundle reload canary | Continuous |
| 4 | 03-05 | 2 / 2 | Full backend pytest suite plus one real released-bundle route canary | Continuous |
| 5 | 03-06 | 2 / 2 | Full backend suite, fresh fail-on-rubric evaluator, then manifest verifier | Continuous |

No wave contains an implementation task without a runnable `<automated>` command, and no three-task window can occur without at least two automated checks.

---

## Wave 0 Requirements

No separate Wave 0 plan is required. Every referenced new test, fixture, evaluator, and verifier is listed in the same task's `<files>` and is created before that task runs its automated command. No plan contains a `MISSING — Wave 0 must create ...` sentinel.

---

## Manual / Downstream Review Prerequisites

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Baseline-creatinine method and creatinine-only limitation wording | PRED-04 | Qualified nephrologist sign-off is unavailable in this autonomous prototype run and must not be fabricated. This is not the Phase 3 execution gate. | Before any clinical use or clinical-validation claim, a nephrologist reviews the source, rule version, baseline method, evidence trace, boundary fixtures, and incomplete-assessment wording; record reviewer identity/date/version or keep status outstanding. |
| Feature/label, synthetic-only, and non-causal SHAP wording | PRED-01, PRED-05 | Clinical/methods judgment is required before clinical use; automated Phase 3 fixtures validate traceability and prohibited wording only. | Before any clinical use or clinical-validation claim, qualified clinical-informatics/methods reviewers inspect the versioned feature/label definition and a nephrologist reviews synthetic-only/non-causal explanation wording; never infer approval from passing tests. |

---

## Validation Sign-Off

- [x] All 12 tasks have a runnable `<automated>` verify command.
- [x] Sampling continuity is complete in Waves 1 through 5.
- [x] No `MISSING` test reference or separate Wave 0 dependency exists.
- [x] No watch-mode flag appears in a verification command.
- [x] The final release gate generates a fresh manifest with `--fail-on-rubric` before verifying it.
- [ ] Focused and full-suite feedback latency measured during execution.
- [ ] All task rows reconciled to green evidence by `$gsd-validate-phase 03`.
- [ ] `status: validated` and `nyquist_compliant: true` set after executed evidence is reconciled.

**Approval:** pending execution and `$gsd-validate-phase 03`
