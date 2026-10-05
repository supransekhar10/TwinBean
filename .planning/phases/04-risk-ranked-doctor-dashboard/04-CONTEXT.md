# Phase 4: Risk-Ranked Doctor Dashboard - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** Autonomous recommendations accepted from the locked phase brief

<domain>
## Phase Boundary

Deliver a doctor-only dashboard for the active synthetic CKD cohort. It must make every monitored patient reachable while putting valid higher 24-hour AKI probabilities first, and make prediction freshness, missingness, and unavailable states visible before the doctor navigates away. This phase does not change clinical-rule logic, prediction logic, model output, Firestore authorization, or create the full patient-detail experience planned for Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Users and Access
- Doctors and nephrologists are the primary users. Preserve Firebase sign-in/sign-out and require the backend's exact `role: doctor` authorization for all dashboard data.
- Browser state is not an authorization decision. Unauthorized, expired, and failed-role-refresh states must block patient data and give the existing role-refresh/sign-in recovery path.
- The dashboard always labels the experience `Research prototype / synthetic data only` and makes no clinical-validation, calibration, prevalence, threshold, or treatment claim.

### Cohort Ordering and Clinical Meaning
- Show all monitored patients from the active synthetic cohort in one dashboard.
- Default ordering is: valid available predictions in descending 24-hour AKI probability, then unavailable predictions; preserve a stable secondary ordering by patient display name. Do not hide unavailable patients or represent them as 0% risk.
- An unavailable prediction displays the exact text `Risk unavailable`, with its returned missingness, staleness, or other reason/warning visible before navigation.
- Render current clinical-rule status in a separately labelled column/region from the future `24-hour AKI risk`; no badge, color, or position may imply that a clinical-rule status is a prediction.
- Show each forecast's prediction generation time before navigation. Do not generate a prediction merely to paint the dashboard; render the most recent authorised stored dashboard snapshot supplied by the backend.

### Visual and Interaction Direction
- Design read: a high-density, calm clinical operating dashboard for doctors, with a light paper surface, restrained teal emphasis, and utilitarian table-first scanning.
- Operate-mode dials are fixed at variance 3, motion 2, and density 6. No purple gradients, glassmorphism, decorative charts, invented risk categories, or invented clinical claims.
- Reuse the existing Next.js, TypeScript, Tailwind 4, CSS-token, Firebase, and authentication patterns. Do not introduce shadcn or a third-party component registry in this phase.
- Desktop and a 390px-wide mobile viewport must work with no horizontal document overflow. On mobile, each patient becomes a vertical summary card rather than a horizontally scrolling table row.
- Motion is limited to immediate press and hover feedback; it is subtle, useful, disabled by `prefers-reduced-motion`, and never delays data, sorting, keyboard navigation, or error recovery.

### Required States
- Define populated, loading skeleton, empty, network error, unauthorised, expired-session, unavailable-risk, stale/missing-data warning, long-content, keyboard/focus, and zero/one/many patient states.
- Loading uses a static table/card-shaped skeleton, never delayed content or a spinner-only layout. Empty, error, and unauthorised states have explicit recovery copy and actions.
- Long patient names, warning text, timestamps, and backend strings must wrap or truncate deliberately without exposing raw error payloads or producing horizontal overflow.

### the agent's Discretion
- Exact page component boundaries, dashboard response DTO name, server-side aggregation implementation, icon treatment, and the concise mapping from trusted reason codes to clinician-readable warning copy may follow project conventions.
- Use the existing CSS token names and values where they meet the contract; add only local dashboard tokens needed for semantic warning and muted states.
- Choose whether the patient navigation control is a whole-row link or an explicit `Open patient` control, provided it is keyboard-operable and its accessible name includes the patient display name.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/auth-panel.tsx` already manages Firebase sign-in/sign-out, doctor role refresh, and accessible request errors.
- `frontend/src/app/globals.css` supplies the light clinical palette (`--paper`, `--surface`, `--ink`, `--muted`, `--accent`, `--focus`), 44px minimum controls, visible focus, and reduced-motion override.
- `backend/app/patient_routes.py` already has protected patient endpoints; `backend/app/prediction_service.py` distinguishes `available` and `unavailable` prediction DTOs, including `generated_at`, `warnings`, and unavailable `reasons`.

### Integration Constraints
- The current `GET /patients` response contains only `patient_id`, `display_name`, `age`, and `ckd_stage`; it cannot safely or efficiently populate dashboard risk, timestamp, warning, and rule columns alone.
- Add a doctor-protected, bounded server-side dashboard projection that joins the active-cohort patient summaries with their latest separate rule and prediction records. The browser must not make an N+1 request sequence or calculate validity/ranking.
- The server determines availability and ordering from the discriminated prediction state. A dashboard record with `status: unavailable` must omit probability and include no fabricated numeric substitute.

</code_context>

<deferred>
## Deferred Ideas

- Patient history, simulated IoT charts, full clinical-rule evidence, prediction details, and SHAP explanations belong to Phase 5.
- Filters, saved views, cohort administration, notification workflows, and researcher-facing evaluation reporting are outside this phase.
- Any real-patient, clinical-deployment, diagnostic, or treatment workflow remains out of scope.

</deferred>
