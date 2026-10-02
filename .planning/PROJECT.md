# TwinBean

## What This Is

TwinBean is a kidney digital twin research prototype for doctors and nephrologists. It combines synthetic longitudinal patient histories with a separate simulated IoT stream to present kidney trends, current clinical rule status, and predicted risk of a new acute kidney injury within 24 hours for adults with chronic kidney disease.

The initial product centers on a doctor dashboard ordered by predicted risk and a patient detail page. Researchers can consume model evaluation reports, but a separate researcher interface is not part of the initial prototype.

## Core Value

Doctors can review trustworthy, clearly separated evidence about a simulated CKD patient's current state and future 24-hour AKI risk without mistaking unavailable predictions for low risk.

## Requirements

### Validated

(None yet ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ship to validate)

### Active

- [ ] Doctors can sign in and sign out with Firebase Authentication using email and password.
- [ ] Protected backend endpoints verify Firebase ID tokens and admit only users whose trusted custom claim contains `role: doctor`.
- [ ] A trusted Firebase Admin SDK script can grant the doctor role; users cannot grant or alter their own role.
- [ ] The first milestone provides runnable Next.js/TypeScript/Tailwind and Python/FastAPI skeletons plus an authenticated backend health check.
- [ ] Firebase configuration, demo-account approval, ID-token refresh, credential handling, and local startup are documented and locally verified.
- [ ] The doctor dashboard lists all monitored patients and defaults to highest predicted 24-hour AKI risk first.
- [ ] Patients without a valid prediction display ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œRisk unavailable,ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â never a zero-risk score.
- [ ] The interface displays prediction time and missing or stale data warnings.
- [ ] Patient detail separates history, simulated IoT trends, current clinical rule results, future predictions, and SHAP explanations.
- [ ] Synthetic patient history and a separate simulated IoT stream feed the research prototype.
- [ ] The model predicts new AKI within 24 hours in adults with CKD using scikit-learn/XGBoost, with SHAP explanations.
- [ ] Evaluation reports contain actual measured model results from synthetic data rather than invented metrics.
- [ ] Patient data is stored in Cloud Firestore and restricted to authenticated, authorized doctors.

### Out of Scope

- Real patient data or clinical deployment ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â this is a synthetic-data research prototype, not a diagnostic medical device.
- A separate researcher interface ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â researchers consume evaluation reports in the initial prototype.
- User-managed roles ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â doctor authorization is assigned only through a trusted Firebase Admin SDK process.
- SQLite ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Cloud Firestore is the project database.
- Building the full prediction and dashboard feature set in the first milestone ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â milestone one stops at the skeleton, authentication, authorization, health checks, documentation, and local verification.

## Context

The prototype must keep present-tense clinical rule outputs distinct from forward-looking model predictions. The dashboard supports triage by sorting valid predictions from highest to lowest risk while retaining access to every monitored patient. Missing, invalid, or stale inputs must remain visible and must never be silently represented as a zero-risk prediction.

The frontend stack is Next.js, TypeScript, Tailwind CSS, and Recharts. The backend is Python with FastAPI. Firebase Authentication provides email/password sign-in; Firebase Admin SDK verifies ID tokens and accesses Cloud Firestore. Modeling uses scikit-learn, XGBoost, and SHAP.

The first implementation milestone is intentionally narrow: create frontend and backend skeletons, implement Firebase sign-in/sign-out, enforce the `role: doctor` claim on a protected backend health check, document Firebase setup and demo-account approval, then verify the flow locally.

## Development Workflow

- GSD manages requirements, milestone structure, planning artifacts, and progress state. Codex implements and verifies the code.
- Each implementation task uses a bounded Ralph-style cycle: implement, check, then fix. After three failed checks, stop with evidence and report the blocker. Never weaken, remove, or bypass tests to claim completion.
- Frontend work loads design guidance only when needed: Taste establishes the visual direction, Emil Kowalski guidance adds subtle useful interactions, and Impeccable audits and refines the working interface.
- Design skills apply only to frontend work. They must preserve clinical meaning, authorization boundaries, and prediction outputs.

## Constraints

- **Data**: Use only synthetic patient and simulated IoT data ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â avoid handling real protected health information.
- **Security**: Verify Firebase ID tokens server-side and require `role: doctor` on protected endpoints ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â authentication alone is insufficient.
- **Credential handling**: Keep Firebase service-account credentials backend-only and out of Git ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â privileged credentials must never reach the browser or repository.
- **Authorization**: Assign custom claims only through trusted Admin SDK code ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â end users cannot self-elevate.
- **Database**: Use Cloud Firestore, replacing any prior SQLite plan ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â one authoritative persistence design avoids drift.
- **Clinical clarity**: Render clinical rules and future risk separately ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â clinicians must be able to distinguish observed rule state from prediction.
- **Prediction semantics**: Show prediction timestamps and missing/stale-data warnings; render invalid predictions as ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œRisk unavailableÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â absence of a score is not zero risk.
- **Evaluation integrity**: Report actual model evaluation outputs ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â do not fabricate performance claims.
- **Initial delivery**: Do not implement the full clinical dashboard or ML pipeline in milestone one ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â establish and verify the secure application boundary first.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Target doctors and nephrologists first | The prototype is designed for clinical review of simulated patient data and predicted AKI risk | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Default dashboard ordering to highest valid predicted risk | Supports rapid review while keeping all monitored patients accessible | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Keep clinical rules separate from predictions | Prevents current rule status from being confused with future model risk | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Use Firebase Authentication plus a trusted `role: doctor` custom claim | Creates an explicit server-enforced authorization boundary | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Use Cloud Firestore instead of SQLite | Aligns persistence with Firebase identity and the agreed deployment direction | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Use synthetic data with actual evaluation results | Enables reproducible research without real-patient privacy exposure or fabricated metrics | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |
| Begin with a secure vertical skeleton | Validates frontend/backend integration, authentication, authorization, and configuration before clinical features | ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Pending |

| Use GSD governance with Codex execution | Keeps project intent and progress traceable while assigning implementation and verification clearly | Ã¢â‚¬â€ Pending |
| Bound task repair cycles to three failed checks | Surfaces blockers without weakening tests or hiding repeated failures | Ã¢â‚¬â€ Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Move to Out of Scope with reason
2. Requirements validated? ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Move to Validated with phase reference
3. New requirements emerged? ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Add to Active
4. Decisions to log? ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Add to Key Decisions
5. ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œWhat This IsÃƒÂ¢Ã¢â€šÂ¬Ã‚Â still accurate? ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â still the right priority?
3. Audit Out of Scope ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-02 after workflow and Phase 1 implementation*
