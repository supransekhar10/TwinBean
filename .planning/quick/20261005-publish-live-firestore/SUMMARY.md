---
status: blocked
date: 2026-10-05
---

# Live Firestore publication summary

The current immutable synthetic cohort was successfully published to Firebase project `twinbean-a7011`:

- 12 patients
- 420 EHR events
- 300 simulated IoT observations
- generator `twinbean-live-v1`, seed 2402
- manifest checksum `114bd27143b100e689ec281fa8a489bfbbeb9897007bc85e68dbcf5cc85b9d04`

Clinical-result publication exposed and fixed a live Firebase transaction-read incompatibility. Twenty-eight focused repository/prediction tests pass after replacing the invalid inactive transaction read with an atomic create-only batch.

The publication retry exceeded its five-minute command window, and the subsequent read-only status check received Firestore `429 RESOURCE_EXHAUSTED: Quota exceeded`. Per the bounded three-attempt workflow, no further live requests were made. Some patient clinical results may have committed atomically before the timeout; the evaluation-report write was not confirmed.

Resume only after Firestore quota is available:

`Set-Location backend; .\.venv\Scripts\python.exe -m scripts.publish_live_demo --expected-project twinbean-a7011 --prediction-cutoff 2026-10-05T00:00:00Z --evaluation-report artifacts\evals\phase6-model-evaluation.json --max-patients 12 --confirm-write`

The command is idempotent for identical deterministic result identities and never deletes unrelated data.
