---
status: complete
quick_id: 261006-v0q
---

# Reviewed patient status

- Review-note writes atomically persist patient-level review metadata in Firestore.
- Dashboard projections expose `latest_review_at` and render a green `Reviewed` badge instead of `Review now`.
- Existing saved review metadata was backfilled for one reviewed patient and synchronized to the local dashboard snapshot.
- Verification: 31 backend tests, 4 focused frontend tests, ESLint, and the Next.js production build passed.