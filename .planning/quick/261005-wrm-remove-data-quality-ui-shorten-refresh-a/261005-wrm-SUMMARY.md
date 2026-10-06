---
status: complete
quick_id: 261005-wrm
commit: 85b4625
---

# Dashboard triage refinements complete

- Removed all visible data-quality columns and warning blocks.
- Simplified the Firestore control to **Refresh**.
- Added search, clinical filters, cohort summary counts, and current-rule priority.
- Surfaced six existing synthetic patients whose current creatinine criteria are met; future risk remains honestly unavailable.
- Added an opt-in two-tone alert with no autoplay.

Verification: 11 frontend tests passed; ESLint, Next.js production build, Impeccable detector, frontend HTTP 200, backend HTTP 200, and 12-patient cache check passed.
