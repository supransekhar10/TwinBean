# Phase 6 Summary

Completed the leakage-resistant synthetic model comparison.

- Dataset: 80 deterministic TwinBean synthetic adult CKD patients; not Synthea.
- Split: 60 training patients and 20 held-out patients, with zero patient overlap.
- Both model variants use the same held-out patients and cutoff.
- Actual EHR-only metrics: ROC AUC 0.605, average precision 0.596, Brier 0.265, log loss 0.744, accuracy 0.550.
- Actual combined-stream metrics: ROC AUC 0.510, average precision 0.629, Brier 0.297, log loss 0.806, accuracy 0.500.
- Results are synthetic-data evaluation only and are not clinical validation.
