# Roadmap: TwinBean

## Overview

TwinBean advances through six vertical phases: establish a secure runnable application boundary, build synthetic kidney data in Firestore, add clinically explicit prediction outputs, deliver risk-ranked doctor workflows, complete the patient digital-twin view, and finish with leakage-resistant comparative evaluation using actual model results.

## Delivery Workflow

- GSD owns requirements, milestones, plans, and progress state; Codex owns implementation and verification.
- Every implementation task follows an implement, check, fix loop with at most three failed checks. A third failure becomes a reported blocker; tests are never weakened to pass.
- Design skills are loaded only for frontend work: Taste for direction, Emil Kowalski guidance for restrained interactions, then Impeccable for audit and refinement of a working interface.
- UI refinement must preserve medical logic, authorization behavior, and prediction outputs.

## Phases

**Phase Numbering:**
- Integer phases are planned milestone work.
- Decimal phases are reserved for urgent insertions.

- [x] **Phase 1: Secure Foundation and Firebase Access** - Run both applications locally and prove doctor-only authenticated backend access. (completed 2026-10-03)
- [x] **Phase 2: Synthetic Kidney Data and Firestore** - Persist separate synthetic EHR and IoT streams behind doctor-only access. (completed 2026-10-04)
- [x] **Phase 3: Clinical Rules and AKI Prediction** - Produce distinct clinical-rule and 24-hour AKI prediction results with safe unavailable states. (completed 2026-10-05)
- [x] **Phase 4: Risk-Ranked Doctor Dashboard** - Let doctors review every monitored patient with valid risks prioritized safely. (completed 2026-10-05)
- [ ] **Phase 5: Patient Digital Twin Detail** - Present history, trends, rules, predictions, warnings, and explanations in distinct sections.
- [ ] **Phase 6: Leakage-Resistant Model Evaluation** - Report actual patient-level, time-safe EHR-only and combined-stream evaluation results.

## Phase Details

### Phase 1: Secure Foundation and Firebase Access

**Goal:** Doctors can sign in to a locally runnable frontend and successfully call a doctor-authorized FastAPI health endpoint.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** FOUND-01, FOUND-02, FOUND-03, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, FIRE-02, FIRE-03, FIRE-04
**Success Criteria** (what must be TRUE):
  1. Developer can start the Next.js frontend and FastAPI backend locally using documented configuration.
  2. Doctor can sign in and sign out with Firebase email/password authentication.
  3. Signed-in doctor with `role: doctor` can call the protected backend health endpoint; missing, invalid, or unauthorized tokens are rejected.
  4. Administrator can grant the doctor claim with a trusted script and follow the documented token-refresh process for a demo account.
  5. Service-account credentials remain backend-only and absent from Git.

**Plans:** 3/3 plans complete
**UI hint:** yes

Plans:
- [x] 01-01: Scaffold locally runnable Next.js and FastAPI applications with configuration boundaries.
- [x] 01-02: Implement Firebase browser authentication and server-side doctor-role enforcement.
- [x] 01-03: Add trusted role-assignment tooling, security tests, local verification, and concise setup documentation.

### Phase 2: Synthetic Kidney Data and Firestore

**Goal:** As a doctor, I want to access synthetic CKD patient histories and a separately modeled simulated IoT stream stored in Firestore, so that I can review aligned synthetic kidney evidence securely.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** FIRE-01, FIRE-05, DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. System loads reproducible synthetic adult CKD histories without using real patient data.
  2. System produces simulated IoT observations as a stream distinct from EHR history.
  3. Prototype data is persisted in Cloud Firestore, with no SQLite dependency.
  4. Only authenticated users carrying the doctor role can read patient data through the backend.

**Plans:** TBD
- [x] 02-01-PLAN.md
- [x] 02-02-PLAN.md
- [x] 02-03-PLAN.md
- [x] 02-04-PLAN.md

### Phase 3: Clinical Rules and AKI Prediction

**Goal:** As a doctor, I want to receive auditable current-rule results and valid 24-hour AKI predictions as separate clinical concepts, so that I can distinguish observed clinical status from future risk.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** PRED-01, PRED-02, PRED-03, PRED-04, PRED-05
**Success Criteria** (what must be TRUE):
  1. A valid synthetic adult CKD record can receive an XGBoost-based prediction for new AKI within 24 hours.
  2. Missing, invalid, or stale inputs produce an explicit unavailable result rather than a zero-risk score.
  3. Current clinical rule outputs are calculated, stored, and returned separately from future risk predictions.
  4. Every valid prediction records its prediction time and produces SHAP feature-attribution data.

**Plans:** TBD
- [x] 03-01-PLAN.md
- [x] 03-02-PLAN.md
- [x] 03-03-PLAN.md
- [x] 03-04-PLAN.md
- [x] 03-05-PLAN.md
- [x] 03-06-PLAN.md

### Phase 4: Risk-Ranked Doctor Dashboard

**Goal:** As a doctor, I want to triage all monitored patients with honest future-risk, freshness, and data-quality information, so that I can prioritize valid high-risk predictions without losing access to other patients.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Doctor can view every monitored synthetic patient from one dashboard.
  2. Patients with valid predictions default to descending 24-hour AKI risk order without hiding other patients.
  3. Patients lacking a valid prediction display "Risk unavailable," never a numeric zero-risk substitute.
  4. Doctor can see prediction time and missing or stale data warnings before opening a patient.

**Plans:** TBD
**UI hint:** yes

### Phase 5: Patient Digital Twin Detail

**Goal:** As a doctor, I want to inspect a simulated patient's complete kidney context in distinct evidence sections, so that I do not conflate observations, clinical rules, future risk, or explanations.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** PAT-01, PAT-02, PAT-03, PAT-04, PAT-05
**Success Criteria** (what must be TRUE):
  1. Doctor can open a patient detail page from the dashboard.
  2. Synthetic history and IoT trends appear in separate, clearly labeled sections and visualizations.
  3. Current clinical rule status and future AKI prediction appear separately with prediction time and data-quality warnings.
  4. SHAP explanations appear separately from the prediction score and identify the features influencing a valid result.

**Plans:** TBD
**UI hint:** yes

### Phase 6: Leakage-Resistant Model Evaluation

**Goal:** As a researcher, I want to inspect reproducible actual evaluation results comparing EHR-only and combined-stream prediction, so that I can assess synthetic model performance under patient-level and time-safe evaluation.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06
**Success Criteria** (what must be TRUE):
  1. Evaluation holds out entire simulated patients rather than mixing one patient's records across dataset splits.
  2. Feature construction uses only observations available at each prediction time and demonstrates checks against future-data leakage.
  3. The same held-out patients are used to compare EHR-history-only and combined EHR-plus-IoT models.
  4. Generated report records dataset construction, split strategy, metrics, limitations, and actual model-run results without placeholder claims.

**Plans:** TBD

## Progress

**Execution Order:** Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5; Phase 6 begins after Phase 3 and completes the milestone.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Secure Foundation and Firebase Access | 3/3 | Complete | 2026-10-03 |
| 2. Synthetic Kidney Data and Firestore | 4/4 | Complete    | 2026-10-04 |
| 3. Clinical Rules and AKI Prediction | 6/6 | Complete    | 2026-10-05 |
| 4. Risk-Ranked Doctor Dashboard | 2/2 | Complete    | 2026-10-05 |
| 5. Patient Digital Twin Detail | 0/TBD | Not started | - |
| 6. Leakage-Resistant Model Evaluation | 0/TBD | Not started | - |
