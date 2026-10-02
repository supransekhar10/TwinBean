# Phase 2: Synthetic Kidney Data and Firestore - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a reproducible synthetic adult CKD dataset, model simulated IoT observations as a distinct stream, persist both in Cloud Firestore, and expose them only through doctor-authorized backend read endpoints. This phase does not calculate clinical rules, predictions, or SHAP explanations.

</domain>

<decisions>
## Implementation Decisions

### Synthetic Cohort Contract
- **D-01:** Use a versioned deterministic generator with a fixed configurable seed and stable synthetic patient IDs so the same inputs reproduce the same cohort.
- **D-02:** Generate adult-only CKD histories with plausible demographics, CKD context, encounters, medications, and longitudinal kidney-relevant laboratory observations.
- **D-03:** Mark generated records explicitly as synthetic and record generator version, seed, and UTC timestamps as provenance. Never derive fixtures from real patient data.

### EHR and IoT Separation
- **D-04:** Store patient identity and cohort summary separately from longitudinal observations.
- **D-05:** Keep EHR events and simulated IoT observations in distinct typed Firestore subcollections with independent event timestamps and source metadata. -- **Reversibility:** costly -- combining these streams later would require a Firestore migration and changes to consumers.
- **D-06:** IoT observations should cover kidney-relevant home monitoring such as weight, blood pressure, and heart rate, while EHR records remain the source for clinical history and laboratory data.

### Firestore Seeding and Provenance
- **D-07:** Provide an explicit backend-only seed command; do not seed implicitly during API startup.
- **D-08:** Make seeding idempotent for the same generator version and seed. Update only deterministic TwinBean-owned documents and never delete or overwrite unrelated Firestore data.
- **D-09:** Cloud Firestore is the authoritative data store. Do not add SQLite or a browser-side persistence path.

### Doctor-Only Read Surface
- **D-10:** Browser code must obtain patient data through FastAPI; it must not query Firestore directly.
- **D-11:** Expose protected patient-list and patient-detail data endpoints using the existing `require_doctor` dependency for exact `role: doctor` authorization.
- **D-12:** Return EHR history and IoT observations as separately named response fields so future interfaces cannot accidentally present them as one source.

### Codex's Discretion
- Choose the small prototype cohort size, observation cadence, exact field constraints, endpoint pagination threshold, and internal Python module layout, provided records remain clinically plausible, deterministic, and sufficient for later model evaluation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and Phase Contract
- `.planning/PROJECT.md` - product intent, security boundary, synthetic-data constraint, and development workflow.
- `.planning/REQUIREMENTS.md` - FIRE-01, FIRE-05, DATA-01, DATA-02, and DATA-03 acceptance requirements.
- `.planning/ROADMAP.md` - Phase 2 boundary, goal, dependencies, and success criteria.

### Existing Firebase Foundation
- `docs/FIREBASE_SETUP.md` - local Firebase project, credentials, demo doctor, and startup configuration.
- `backend/app/firebase.py` - process-wide Firebase Admin application initialization to reuse for Firestore.
- `backend/app/auth.py` - verified-token and exact doctor-role authorization dependency.
- `backend/app/main.py` - existing FastAPI application and protected-route pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_firebase_app()` in `backend/app/firebase.py`: reuse the initialized Admin SDK app when obtaining a Firestore client.
- `require_doctor()` in `backend/app/auth.py`: apply unchanged to every patient-data route.
- FastAPI app in `backend/app/main.py`: mount the new router without altering the verified health endpoints.

### Established Patterns
- Settings come from backend environment variables through `backend/app/settings.py`.
- Backend modules use typed functions and dependency injection; tests replace Firebase boundaries rather than contacting live services.
- Firebase credentials remain Application Default Credentials on the server and are never copied into browser configuration.

### Integration Points
- Add Firestore access and patient routes under `backend/app/`, seed tooling under `backend/scripts/`, and focused tests under `backend/tests/`.
- Extend `docs/FIREBASE_SETUP.md` only with the Firestore enablement, indexes if required, and seed/run instructions.

</code_context>

<specifics>
## Specific Ideas

- Stable synthetic identifiers and timestamps should make later patient-level model splits and leakage checks reproducible.
- Data-source separation must remain visible from Firestore documents through API response models.

</specifics>

<deferred>
## Deferred Ideas

- Clinical rules, AKI prediction, prediction availability, and SHAP explanations belong to Phase 3.
- Dashboard ordering and patient-detail presentation belong to Phases 4 and 5.

</deferred>

---

*Phase: 2-Synthetic Kidney Data and Firestore*
*Context gathered: 2026-10-03*
