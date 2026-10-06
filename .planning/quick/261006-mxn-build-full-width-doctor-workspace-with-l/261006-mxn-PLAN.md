# Quick Task 261006-mxn Plan

## Goal

Create a full-width clinician workspace with the supplied TwinBean logo, persistent navigation, and a safe session-only synthetic-patient entry flow while preserving doctor authorization and honest prediction semantics.

## Tasks

1. Add a responsive application shell and sidebar with dashboard navigation, refresh, add-patient, account, and sign-out actions.
2. Add a constrained synthetic-patient form that creates session-only dashboard records with no invented rule or model result.
3. Integrate the supplied logo and refine desktop/mobile styles without changing authentication behavior.
4. Add/update tests and run frontend test, lint, build, and UI quality checks.

## Guardrails

- Do not invent prediction probabilities or clinical rule results.
- New entries are explicitly synthetic and session-only; Firestore refresh restores the authoritative cohort.
- Preserve backend-enforced `role: doctor` authorization.
