# Phase 03 Source Coverage Audit

This audit assigns stable D-01 through D-16 identifiers to the ordered locked-decision bullets in `03-CONTEXT.md`; those identifiers are cited in the executable plans for traceability.

| Source | ID | Feature / Requirement | Plan | Status | Notes |
|---|---|---|---|---|---|
| GOAL | — | Doctor receives auditable current-rule results and valid 24-hour AKI predictions as separate clinical concepts. | 03-01 through 03-06 | COVERED | Tracer establishes separation; expansions deliver the model and release gate. |
| REQ | PRED-01 | Predict new AKI within 24 hours for synthetic adults with CKD. | 03-02, 03-03, 03-04, 03-05, 03-06 | COVERED | Strict cutoff labels, XGBoost bundle, valid inference, contract gate. |
| REQ | PRED-02 | Use scikit-learn/XGBoost and explicitly handle invalid, missing, or stale inputs. | 03-03, 03-04, 03-05, 03-06 | COVERED | Exact pins, preflight, artifact barrier, failure matrix. |
| REQ | PRED-03 | Unavailable is distinct from zero risk. | 03-01, 03-03, 03-05, 03-06 | COVERED | Discriminated union and adversarial tests forbid numeric fallback. |
| REQ | PRED-04 | Calculate, store, and return rules and predictions as distinct result types. | 03-01, 03-02, 03-05, 03-06 | COVERED | Separate DTOs, paths, endpoints, and atomic pair writes. |
| REQ | PRED-05 | Produce SHAP attributions for valid predictions. | 03-04, 03-05, 03-06 | COVERED | Exact name/order and raw-margin additivity gate. |
| CONTEXT | D-01 | Versioned authoritative KDIGO creatinine criteria with exact source. | 03-01, 03-02 | COVERED | Source/version/evidence are required result fields. |
| CONTEXT | D-02 | Assess only supported criteria; never imply urine-output assessment. | 03-01, 03-02 | COVERED | Creatinine-only limitation and wording review. |
| CONTEXT | D-03 | Current rule is not the future prediction response shape. | 03-01, 03-02, 03-05 | COVERED | Separate types and exact serialized key-set tests. |
| CONTEXT | D-04 | Persist rule inputs, times, status, evidence, source, version, limitations. | 03-01, 03-02 | COVERED | ClinicalRuleResult contract and fixtures. |
| CONTEXT | D-05 | Predict a new event strictly within 24 hours after explicit cutoff. | 03-02, 03-03, 03-05 | COVERED | Terminal scenarios and strict open-interval label builder. |
| CONTEXT | D-06 | Valid result has probability/time/model/schema/freshness/warnings and separate SHAP. | 03-04, 03-05 | COVERED | Available union plus engine integration. |
| CONTEXT | D-07 | Missing/invalid/stale/future/schema/artifact/SHAP failure is unavailable, never zero. | 03-01, 03-03, 03-04, 03-05, 03-06 | COVERED | Preflight, typed errors, union, and reference failures. |
| CONTEXT | D-08 | IDs, outcomes, future values, scenario metadata, and rule outputs never enter model features. | 03-02, 03-03, 03-06 | COVERED | Exact allowlist and leakage assertions. |
| CONTEXT | D-09 | Use sklearn-compatible preprocessing, XGBoost, and non-causal SHAP. | 03-04, 03-05 | COVERED | Exact AI-SPEC pipeline and TreeExplainer contract. |
| CONTEXT | D-10 | Explicit seeds and checksum-verifiable versioned artifacts/schema; no untrusted deserialization. | 03-02, 03-03, 03-04 | COVERED | Deterministic scenarios, package provenance, trusted bundle barrier. |
| CONTEXT | D-11 | Phase 3 may train inference model; formal EHR-only vs combined held-out evaluation remains Phase 6. | 03-03, 03-04, 03-05, 03-06 | COVERED | Combined-stream inference artifact and contract-only manifest; no formal comparative performance evaluation. |
| CONTEXT | D-12 | Tests cover valid inference, unavailable states, cutoff/allowlist, separation, persistence, explanation. | 03-01 through 03-06 | COVERED | Focused tests plus 24+ scenario final gate. |
| CONTEXT | D-13 | Extend Phase 2 active-cohort repository; no parallel database or SQLite. | 03-01, 03-05 | COVERED | PatientRepository remains the sole persistence boundary. |
| CONTEXT | D-14 | Store rules and predictions in separate owned subcollections. | 03-01, 03-05 | COVERED | `clinical_rules` and `aki_predictions` with distinct reads. |
| CONTEXT | D-15 | Backend-only endpoints require exact role: doctor. | 03-01, 03-05, 03-06 | COVERED | Direct dependency ordering and denial short-circuit tests. |
| CONTEXT | D-16 | Preserve old cohorts/unrelated data; failures do not corrupt pointer or turn unavailable into a number. | 03-01, 03-05, 03-06 | COVERED | Atomic-batch failure/canary/pointer tests. |
| RESEARCH | — | Add deterministic daily terminal creatinine and cutoff-aligned source observations. | 03-02 | COVERED | At least eight days, both label classes, no embedded labels. |
| RESEARCH | — | Use a versioned 24-hour required-observation freshness policy. | 03-03 | COVERED | Named policy object and exact-boundary tests. |
| RESEARCH | — | Preserve source-specific EHR/IoT snapshots and include cutoff-safe `latest_systolic_bp_mmhg` in the reviewed Phase 3 combined-stream allowlist. | 03-02, 03-03, 03-04, 03-05, 03-06 | COVERED | PRED-01 uses both streams; formal EHR-only-versus-combined comparison remains Phase 6. |
| RESEARCH | — | Verify controlled artifact location, complete manifest, checksums, package/schema/cohort compatibility before joblib load. | 03-04 | COVERED | Tamper tests assert pre-deserialization failure. |
| RESEARCH | — | Validate SHAP in raw-margin space with exact transformed order and 1e-6 additivity tolerance. | 03-04 | COVERED | Any failure invalidates the forecast. |
| RESEARCH | — | Atomically batch one rule plus one forecast without active-pointer mutation. | 03-01, 03-05 | COVERED | Tracer proves architecture; integration completes behavior. |
| RESEARCH | — | Offload synchronous model/SHAP work and bound request concurrency. | 03-05 | COVERED | AnyIO thread worker plus capacity limiter. |
| RESEARCH | — | Create 24+ rule/valid/unavailable/integrity reference cases and immutable contract manifest. | 03-06 | COVERED | Contract evaluation only, not Phase 6 performance evaluation. |
| RESEARCH | — | Use automated traceability/wording fixtures as the autonomous Phase 3 release gate and retain nephrologist review as outstanding before clinical use or any clinical-validation claim. | 03-02, 03-06 | COVERED | No named approval is fabricated and human sign-off does not block this autonomous implementation run. |
| RESEARCH | — | Exact official pandas/sklearn/XGBoost/SHAP pins require provenance verification. | 03-03 | COVERED | Explicit user authorization removes interactive checkpoint; exact identity/version/provenance checks remain. |

## Exclusions (not gaps)

- Doctor dashboard ranking and summary UI: Phase 4.
- Patient-detail charts, replay, and presentation sections: Phase 5.
- Formal patient-held-out EHR-only versus combined-stream metrics/report: Phase 6.
- Optional AI copilot and dedicated researcher interface: outside this phase/milestone scope.

## Audit Result

All Phase 03 GOAL, PRED requirements, locked CONTEXT decisions, and in-scope RESEARCH features/constraints are covered. No unplanned source item remains.
