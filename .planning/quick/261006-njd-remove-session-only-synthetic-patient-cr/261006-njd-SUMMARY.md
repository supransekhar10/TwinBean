---
status: complete
quick_id: 261006-njd
commit: ad1572e
---

# Session-only patient creation removed

- Removed the sidebar action and `/patients/new` route.
- Removed session-storage patient creation, draft fields, draft badges, and unused form styles.
- Dashboard and patient lists now contain only backend/Firestore cohort data.

Verification: 11 tests passed; ESLint passed; production build passed with no `/patients/new` route; current `/patients` returned HTTP 200; one frontend listener remains.
