# TwinBean Synthetic Model Evaluation

> Research prototype using synthetic data only. These results are not clinical validation.

## Design

- Dataset: 80 deterministic synthetic adult CKD patients; generator is not Synthea.
- Split: 60 training and 20 held-out patients; overlap 0.
- Both models use the same held-out patients and the same time-safe cutoff.
- EHR-only excludes the simulated IoT blood-pressure feature; combined includes it.

## Actual Held-Out Results

| Model | ROC AUC | Average precision | Brier score | Log loss | Accuracy at 0.5 |
|---|---:|---:|---:|---:|---:|
| ehr_only | 0.605 | 0.596 | 0.265 | 0.744 | 0.550 |
| combined_ehr_iot | 0.510 | 0.629 | 0.297 | 0.806 | 0.500 |

## Leakage Controls

- Entire patients are held out; no patient appears in both partitions.
- Feature snapshots include only observations at or before prediction time.
- Labels use the open next-24-hour window and are never model features.
- Patient identifiers remain grouping metadata outside the feature matrix.

## Limitations

- Synthetic data evaluation is not clinical validation.
- The deterministic generator has simplified trajectories and does not represent real prevalence or care processes.
- The 0.5 accuracy threshold is descriptive only and is not a clinical decision threshold.
