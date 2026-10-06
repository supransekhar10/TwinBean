---
status: complete
quick_id: 261006-mxn
commit: 7f2c018
---

# Full-width clinician workspace complete

- Replaced the centered dashboard shell with a full-width, responsive clinician workspace and persistent left navigation.
- Integrated the supplied TwinBean kidney logo.
- Moved refresh, account context, and sign-out into the navigation.
- Added a constrained session-only synthetic-patient form. New records explicitly have no clinical rule and show `Risk unavailable`; refresh restores the authoritative Firestore cohort.
- Preserved current-rule and future-prediction separation and doctor-only authentication behavior.

Verification: 11 frontend tests passed; ESLint passed; Next.js production build passed; Impeccable detector reported no findings; `git diff --check` passed.
