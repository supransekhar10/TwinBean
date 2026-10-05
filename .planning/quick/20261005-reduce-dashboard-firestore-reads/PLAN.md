---
status: complete
---

# Reduce dashboard Firestore reads

- Reuse one repository and Firestore client across protected requests.
- Resolve the active cohort once per uncached dashboard load.
- Avoid redundant patient-root reads for already validated list entries.
- Cache the validated dashboard projection for five minutes.
- Invalidate cached projections after cohort or clinical-result writes.

