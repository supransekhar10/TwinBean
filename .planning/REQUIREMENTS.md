# Requirements: TwinBean

**Defined:** 2026-10-02
**Core Value:** Doctors can review trustworthy, clearly separated evidence about a simulated CKD patient's current state and future 24-hour AKI risk without mistaking unavailable predictions for low risk.

## v1 Requirements

### Application Foundation

- [x] **FOUND-01**: Developer can run a Next.js application using TypeScript and Tailwind CSS locally.
- [x] **FOUND-02**: Developer can run a Python FastAPI service locally.
- [x] **FOUND-03**: Frontend can call the backend through a documented local configuration.

### Authentication and Authorization

- [x] **AUTH-01**: Doctor can sign in with a Firebase email/password account.
- [x] **AUTH-02**: Signed-in doctor can sign out and the frontend clears the authenticated session.
- [x] **AUTH-03**: Frontend sends the current Firebase ID token to protected backend endpoints.
- [x] **AUTH-04**: Backend verifies Firebase ID tokens using the Firebase Admin SDK before serving protected endpoints.
- [x] **AUTH-05**: Backend denies protected access unless the verified token contains `role: doctor`.
- [x] **AUTH-06**: Administrator can assign `role: doctor` through a trusted backend-only Admin SDK script.
- [x] **AUTH-07**: User cannot assign or modify their own authorization role.
- [x] **AUTH-08**: Doctor can call an authenticated health endpoint and receive a successful response only with a valid authorized token.

### Firebase Setup and Security

- [x] **FIRE-01**: Backend accesses Cloud Firestore through the Firebase Admin SDK.
- [x] **FIRE-02**: Service-account credentials remain backend-only, are excluded from Git, and are never exposed to the browser.
- [x] **FIRE-03**: Setup documentation explains Firebase project configuration, email/password enablement, environment variables, and local startup.
- [x] **FIRE-04**: Setup documentation explains how to approve a demo doctor account and refresh its ID token after assigning the claim.
- [x] **FIRE-05**: Patient data access is limited to authenticated users authorized as doctors.

### Doctor Dashboard

- [ ] **DASH-01**: Doctor can view all monitored synthetic patients in one dashboard.
- [ ] **DASH-02**: Dashboard defaults to patients with valid predictions ordered from highest to lowest predicted 24-hour AKI risk.
- [ ] **DASH-03**: Patients without a valid prediction remain accessible and display “Risk unavailable” rather than a zero-risk score.
- [ ] **DASH-04**: Dashboard displays each prediction's generation time.
- [ ] **DASH-05**: Dashboard warns when required patient or IoT data is missing or stale.

### Patient Detail

- [ ] **PAT-01**: Doctor can open a patient detail page from the dashboard.
- [ ] **PAT-02**: Patient detail presents synthetic longitudinal history separately from simulated IoT trends.
- [ ] **PAT-03**: Patient detail presents current clinical rule status separately from future model predictions.
- [ ] **PAT-04**: Patient detail presents prediction time and missing or stale data warnings.
- [ ] **PAT-05**: Patient detail presents SHAP explanations in a section separate from the prediction score.

### Synthetic Data and Prediction

- [x] **DATA-01**: System generates or loads synthetic histories for adult patients with chronic kidney disease.
- [x] **DATA-02**: System produces a simulated IoT stream independently from patient history data.
- [x] **DATA-03**: System stores prototype patient, observation, rule, and prediction data in Cloud Firestore rather than SQLite.
- [x] **PRED-01**: Model predicts whether a new acute kidney injury will occur within 24 hours for an adult with chronic kidney disease.
- [ ] **PRED-02**: Prediction pipeline uses scikit-learn and XGBoost with explicit handling for invalid, missing, or stale inputs.
- [x] **PRED-03**: Prediction output preserves “unavailable” as a distinct state and never converts it to zero risk.
- [x] **PRED-04**: Current clinical rules and future model predictions are calculated, stored, and returned as distinct result types.
- [ ] **PRED-05**: Prediction pipeline produces SHAP feature-attribution data for valid predictions.

### Evaluation

- [ ] **EVAL-01**: Researcher can review an evaluation report generated from actual model runs on synthetic held-out data.
- [ ] **EVAL-02**: Evaluation report identifies dataset construction, split strategy, metrics, and limitations.
- [ ] **EVAL-03**: Evaluation report contains no invented or placeholder performance claims presented as results.
- [ ] **EVAL-04**: Model evaluation uses patient-level splits so records from one simulated patient cannot appear across training and held-out sets.
- [ ] **EVAL-05**: Feature construction and evaluation prevent future observations from leaking into an earlier prediction time.
- [ ] **EVAL-06**: Evaluation compares an EHR-history-only model with a combined EHR-history-plus-IoT-stream model on the same held-out patients.

## v2 Requirements

### Research Experience

- **RSCH-01**: Researcher can use a dedicated interface for experiments and model comparisons.
- **RSCH-02**: Researcher can manage dataset versions and compare evaluation runs interactively.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real patient or protected health data | The initial system is a synthetic-data research prototype. |
| Clinical diagnosis or production decision support | Regulatory validation and real-world clinical validation are outside this prototype. |
| Separate researcher interface | Evaluation reports are sufficient for v1. |
| User-managed role assignment | Only trusted Admin SDK code may grant the doctor role. |
| SQLite persistence | Cloud Firestore is the agreed database. |
| Full dashboard, IoT, or ML implementation in Phase 1 | The first phase is limited to the secure runnable skeleton and health-check flow. |

## Definition of Done

- Each v1 requirement is implemented in its mapped phase and verified with automated or documented manual checks.
- Security-sensitive endpoints reject missing, invalid, and unauthorized tokens.
- Documentation is concise, reproducible, and contains no committed secrets.
- Reported model metrics come from preserved evaluation output generated by the implemented pipeline.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| AUTH-06 | Phase 1 | Complete |
| AUTH-07 | Phase 1 | Complete |
| AUTH-08 | Phase 1 | Complete |
| FIRE-01 | Phase 2 | Complete |
| FIRE-02 | Phase 1 | Complete |
| FIRE-03 | Phase 1 | Complete |
| FIRE-04 | Phase 1 | Complete |
| FIRE-05 | Phase 2 | Complete |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |
| PAT-01 | Phase 5 | Pending |
| PAT-02 | Phase 5 | Pending |
| PAT-03 | Phase 5 | Pending |
| PAT-04 | Phase 5 | Pending |
| PAT-05 | Phase 5 | Pending |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| PRED-01 | Phase 3 | Complete |
| PRED-02 | Phase 3 | Pending |
| PRED-03 | Phase 3 | Complete |
| PRED-04 | Phase 3 | Complete |
| PRED-05 | Phase 3 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 6 | Pending |
| EVAL-03 | Phase 6 | Pending |
| EVAL-04 | Phase 6 | Pending |
| EVAL-05 | Phase 6 | Pending |
| EVAL-06 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-02*
*Last updated: 2026-10-02 after roadmap creation*
