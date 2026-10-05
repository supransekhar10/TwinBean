# TwinBean

## What This Is

TwinBean is a kidney digital twin research prototype for doctors and nephrologists. It combines synthetic longitudinal patient histories with a separate simulated IoT stream to present kidney trends, current clinical rule status, and predicted risk of a new acute kidney injury within 24 hours for adults with chronic kidney disease.

The initial product centers on a doctor dashboard ordered by predicted risk and a patient detail page. Researchers consume model evaluation reports, but a separate researcher interface is outside the initial prototype.

## Core Value

Doctors can review trustworthy, clearly separated evidence about a simulated CKD patient's current state and future 24-hour AKI risk without mistaking unavailable predictions for low risk.

## Requirements

### Validated

- [x] Doctors can sign in and sign out with Firebase email/password authentication. -- Phase 1
- [x] Protected backend endpoints verify Firebase ID tokens and require the trusted custom claim `role: doctor`. -- Phase 1
- [x] A trusted Firebase Admin SDK script can grant the doctor role; users cannot grant or alter their own role. -- Phase 1
- [x] Next.js/TypeScript/Tailwind and FastAPI skeletons run locally with public and authenticated health checks. -- Phase 1
- [x] Firebase setup, demo-account approval, ID-token refresh, credential handling, and local startup are documented and verified. -- Phase 1

### Active

- [ ] Doctors can load the dashboard and revisited patient records from a backend-only local synthetic snapshot.
- [ ] Doctors can explicitly replace the snapshot from authoritative Firestore data without losing a valid snapshot when refresh fails.
- [ ] Patient identity, kidney measures, IoT trends, and SHAP influence are more informative without inventing clinical evidence.

### Out of Scope

- Real patient data or clinical deployment -- this is a synthetic-data research prototype, not a diagnostic medical device.
- A separate researcher interface -- researchers consume evaluation reports in the initial prototype.
- User-managed roles -- doctor authorization is assigned only through trusted Firebase Admin SDK code.
- SQLite -- Cloud Firestore is the authoritative database.

## Context

The first six phases delivered the secure synthetic-data prototype, doctor dashboard, patient digital twin, and measured evaluation. The current milestone improves responsiveness and clinical readability while keeping Firestore authoritative and authorization unchanged.

The prototype must keep present-tense clinical rule outputs distinct from forward-looking predictions. Missing, invalid, or stale inputs must remain visible and must never be represented as zero risk.

The frontend stack is Next.js, TypeScript, Tailwind CSS, and Recharts. The backend is Python with FastAPI. Firebase Authentication provides email/password sign-in; Firebase Admin SDK verifies ID tokens and accesses Cloud Firestore. Modeling uses scikit-learn, XGBoost, and SHAP.

## Development Workflow

- GSD manages requirements, milestone structure, planning artifacts, and progress state. Codex implements and verifies code.
- Each implementation task uses a bounded Ralph-style cycle: implement, check, then fix. After three failed checks, stop with evidence and report the blocker. Never weaken, remove, or bypass tests to claim completion.
- Frontend work loads design guidance only when needed: Taste establishes direction, Emil Kowalski guidance adds subtle useful interactions, and Impeccable audits and refines the working interface.
- Design skills apply only to frontend work and must preserve clinical meaning, authorization boundaries, and prediction outputs.

## Constraints

- **Data**: Use only synthetic patient and simulated IoT data.
- **Security**: Verify Firebase ID tokens server-side and require `role: doctor`; authentication alone is insufficient.
- **Credential handling**: Keep Firebase service-account credentials backend-only and out of Git.
- **Authorization**: Assign custom claims only through trusted Admin SDK code.
- **Database**: Use Cloud Firestore, not SQLite.
- **Clinical clarity**: Keep clinical rules and future risk separate.
- **Prediction semantics**: Show prediction timestamps and missing/stale-data warnings; invalid predictions show "Risk unavailable."
- **Evaluation integrity**: Report actual model evaluation outputs and prevent leakage.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Target doctors and nephrologists first | The prototype supports clinical review of simulated patient data and AKI risk | Pending |
| Default dashboard ordering to highest valid predicted risk | Supports rapid review while keeping all monitored patients accessible | Pending |
| Keep clinical rules separate from predictions | Prevents current rule status from being confused with future model risk | Pending |
| Use Firebase Authentication plus `role: doctor` | Creates an explicit server-enforced authorization boundary | Validated in Phase 1 |
| Use Cloud Firestore instead of SQLite | Aligns persistence with Firebase identity and the agreed deployment direction | Pending Phase 2 |
| Use synthetic data with actual evaluation results | Avoids real-patient exposure and fabricated metrics | Pending |
| Begin with a secure vertical skeleton | Validates integration and authorization before clinical features | Validated in Phase 1 |
| Use GSD governance with Codex execution | Keeps intent and progress traceable | Active |
| Bound task repair cycles to three failed checks | Surfaces blockers without weakening tests | Active |
| Keep a backend-only local synthetic snapshot | Makes repeated reads fast without exposing privileged credentials or introducing a second authoritative database | Active |
| Replace cached data only after a successful Firestore refresh | Prevents a transient Firebase failure from destroying the last usable snapshot | Active |
| Keep the initial prototype doctor-only | The hackathon brief asks for a conceptual doctor dashboard; an assistant role would expand authorization scope without a demonstrated need | Active |

---
*Last updated: 2026-10-05 for the fast informative doctor experience milestone*
