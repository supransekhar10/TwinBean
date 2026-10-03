# Phase 2 hackathon data audit

Status: requirements satisfied offline; live Firestore evidence remains the existing Phase 2 Plan 02-04 checkpoint.

| Requirement | Result | Evidence |
|---|---|---|
| Historical synthetic EHR records | PASS | `generate_cohort` creates encounters, medication history, and six monthly kidney laboratory panels per patient. |
| Separate wearable/medical-IoT time series | PASS | Eight weekly weight, blood-pressure, and heart-rate sets use `IotObservation`, `twinbean-simulated-iot`, and `iot_observations`. |
| Matching patient IDs | PASS | Both stream types carry the stable generated `patient_id`; the alignment regression test requires each stream's patient-ID set to equal the cohort set. |
| Aligned timestamps | PASS | Both streams derive timezone-aware UTC timestamps from the same explicit `time_basis`; tests require bounded overlapping time windows. Exact timestamp equality is not assumed. |
| Generator, seed, units, assumptions, limitations documented | PASS | `docs/SYNTHETIC_DATA.md`. |
| Synthea provenance claim | PASS | No Synthea code or dependency is present; documentation identifies the project-local generator and explicitly says Synthea was not used. |

No missing stream implementation was found. The Phase 2 generator and Firestore manifest already keep EHR and IoT data separate.

## Locked downstream contract

- The production prediction path must consume both streams; EHR-only is a comparison baseline, not the final combined model.
- Split by patient ID before fitting or preprocessing.
- Build features using only data available at each prediction cutoff; exclude the following 24-hour label window from features.
- Compare EHR-only and combined-stream models on identical held-out patients and cutoffs.
- Publish actual held-out metrics as **synthetic-data evaluation**, never clinical validation.

These items are already represented by EVAL-01 through EVAL-06 and Phase 6 of the roadmap; this audit makes them an explicit pre-training gate.
