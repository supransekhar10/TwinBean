---
status: complete
quick_id: 261006-o1z
commit: 9258712
---

# Doctor review-note persistence fixed

- Root cause: note writes rescanned the entire immutable cohort and hit the three-second Firestore stream deadline before writing.
- Preserved full cohort validation for normal cohort reads and activation.
- Moved authored notes to the owned `twinbean_doctor_reviews/{patient_id}/notes` collection and validates the stable patient through a verified local snapshot or active cohort.
- Live Firestore verification created the note, read it back, and deleted the exact temporary diagnostic note.

Verification: 41 backend repository/route/dashboard tests passed; live Firestore write/read/delete passed; `git diff --check` passed.
