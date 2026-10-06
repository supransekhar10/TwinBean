---
status: resolved
trigger: "Doctor review note is not saving; UI shows Note could not be saved. Check Firestore and retry."
created: 2026-10-06
updated: 2026-10-06
---

## Symptoms

- Expected: Clicking Save review note persists the authenticated doctor's note and the note remains visible after reload.
- Actual: The UI displays "Note could not be saved. Check Firestore and retry." and no note appears.
- Error: Frontend generic Firestore save failure message.
- Timeline: Reported against the currently running local application.
- Reproduction: Open a patient, enter a review note, click Save review note.

## Current Focus

- hypothesis: The running backend or request path differs from the recently tested review-note implementation.
- test: Inspect live backend logs and exercise the protected review-note endpoint.
- expecting: A concrete HTTP or Firestore error identifying the failing boundary.
- next_action: resolved

## Evidence


## Eliminated


## Resolution

- root_cause:
- fix:
- verification:
- files_changed:
