---
status: complete
quick_id: 261006-n6l
commit: 3557bca
---

# Dedicated full-width clinician pages complete

- Sidebar navigation now uses real routes for Overview (`/dashboard`), Monitored patients (`/patients`), and Add synthetic patient (`/patients/new`).
- Added a reusable navigation shell with consistent active state, logo, account context, and sign-out.
- Patient detail, loading, error, and authorization states now use the same full-width clinician layout.
- Session-only synthetic entries persist across the add-to-list page transition; Firestore refresh clears only temporary session entries.

Verification: 11 frontend tests passed; ESLint passed without warnings; Next.js production build generated all six routes; Impeccable detector and `git diff --check` passed.
