---
status: complete
quick_id: 261006-nf7
commit: cf5e824
---

# Clinician workspace presentation fixed

- Confirmed the missing patient-detail sidebar was caused by duplicate old and new frontend listeners on port 3000; replaced both with one current production server.
- Enriched Overview with review-priority patients and separated evidence-status facts.
- Simplified EHR history to the latest eight records without an internal scroll area.
- Added a model-input readiness panel when SHAP is unavailable, explicitly avoiding fabricated SHAP values.

Verification: 11 tests passed; ESLint and Next.js production build passed; all authenticated route shells returned HTTP 200; one current port-3000 listener remains; Impeccable detector and `git diff --check` passed.
