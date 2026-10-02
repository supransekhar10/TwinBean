# Walking Skeleton — TwinBean

**Phase:** 1
**Generated:** 2026-10-02

## Capability Proven End-to-End

A Firebase-authenticated doctor can sign in through the Next.js UI and receive an authorized response from a protected FastAPI health endpoint.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend | Next.js App Router, TypeScript, Tailwind CSS | Matches the agreed web stack and supports a small client-side auth boundary. |
| Backend | Python FastAPI | Matches the agreed API/ML stack and provides dependency-based authorization. |
| Identity data | Firebase Authentication user directory and custom claims | Phase 1 proves a real privileged read/write through token verification and claim assignment; patient Firestore data starts in Phase 2. |
| Auth | Firebase email/password plus server-enforced `role: doctor` | Authentication and authorization remain distinct and backend-enforced. |
| Local integration | Explicit API base URL and CORS origin | Keeps frontend/backend configuration visible and testable. |
| Directory layout | `frontend/` and `backend/` | Separates browser-visible configuration from privileged backend code. |

## Stack Touched in Phase 1

- [ ] Project scaffold, lint, builds, and test runners
- [ ] Public and protected backend routes
- [ ] Firebase Auth user read and trusted custom-claim write
- [ ] Interactive sign-in/sign-out and authenticated health check
- [ ] Documented local full-stack commands

## Out of Scope

- Patient records and Firestore collections
- Simulated IoT stream
- Clinical rules and AKI model
- Doctor dashboard and patient detail UI
- Research evaluation reports

## Subsequent Slice Plan

- Phase 2 adds separate synthetic EHR and IoT data in Firestore.
- Phase 3 adds clinical rules and 24-hour AKI prediction.
- Phases 4–5 add doctor dashboard and patient detail workflows.
- Phase 6 adds leakage-resistant comparative evaluation.
