# TwinBean synthetic dataset

TwinBean uses a project-local deterministic generator. It does **not** use Synthea, real patient records, or external datasets.

## Generator and seed

`backend/app/synthetic_data.py` exposes `generate_cohort(seed, generator_version, time_basis, patient_count)`. The same four inputs produce the same patient, EHR-event, and IoT-observation IDs, values, UTC timestamps, and serialized payloads. Changing the seed changes the cohort.

For a local demonstration while Firestore is temporarily unavailable, run `python -m scripts.build_local_demo_snapshot` from `backend`. This writes an ignored, backend-only cache explicitly labeled `local_deterministic_synthetic_fallback`. It contains both streams and marks predictions unavailable; it is not represented as Firestore data or clinical validation. A later successful **Refresh from Firestore** replaces the dashboard snapshot and invalidates the fallback patient cache.

The explicit backend command is:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.seed_synthetic_data --seed 2402 --generator-version phase2-v1 --time-basis 2026-01-01T00:00:00+00:00 --patient-count 12
```

The command validates the complete manifest before opening a Firestore batch. It derives an immutable `cohort_id`, stages only these owned versioned paths, reads them back, validates every document and the manifest checksum, then atomically publishes exactly one active pointer:

- `twinbean_cohorts/{cohort_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/ehr_events/{event_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/iot_observations/{observation_id}`
- `twinbean_metadata/active_cohort`

Every root and child stores exact `synthetic: true`, source, generator version, seed, cohort ID, and UTC timestamp provenance. EHR records must use `twinbean-synthetic-ehr`; IoT observations must use `twinbean-simulated-iot`. A malformed or mismatched record makes the staged/active cohort unavailable rather than being coerced into synthetic data.

The generator emits 51 clinical documents per patient (one root, 26 EHR events, and 24 IoT observations). At 100 patients, seeding stages 5,100 clinical documents plus the cohort descriptor and makes one active-pointer transaction: 5,102 total writes, with staged batches bounded at 100 writes. It performs no collection-wide delete or reset and keeps old cohort versions intact. Service-account credentials remain backend-only and are not generator inputs.

## Streams and alignment

Each synthetic patient has the same stable `tbp-...` identifier in both streams. All timestamps are UTC and derive from the supplied `time_basis`, so records can be joined by patient ID and compared using a common temporal cutoff.

- Historical EHR: one nephrology encounter, one medication record, and six monthly panels containing creatinine, eGFR, BUN, and potassium.
- Simulated wearable/medical-IoT: eight weekly sets of weight, blood pressure, and heart rate observations.
- Separation: EHR and IoT use different models, identifiers, source labels, Firestore subcollections, and API fields.

## Units

| Measurement | Unit |
|---|---|
| Creatinine | mg/dL |
| eGFR | mL/min/1.73m2 |
| BUN | mg/dL |
| Potassium | mmol/L |
| Weight | kg |
| Blood pressure | mmHg |
| Heart rate | bpm |

## Assumptions and limitations

- Patients are synthetic adults aged 42–84 with CKD stages G3a, G3b, or G4.
- Values are sampled from simple stage-specific or broad home-monitoring ranges; they are not learned from clinical data.
- The current generator does not model realistic correlations, treatment effects, missingness, sensor error, irregular sampling, comorbidities, or care pathways.
- Sex is currently represented by a limited binary synthetic field.
- The streams overlap in time and share a UTC reference basis, but observations are not necessarily recorded at the exact same instant.
- Phase 2 does not yet generate AKI outcomes or claim predictive/clinical validity.
- Any later metrics are synthetic-data research evaluation only, not clinical validation or evidence of real-world performance.

## Pre-training evaluation contract

Before model training is accepted:

1. Features must include historical EHR inputs and the separate IoT stream. An EHR-only model may exist only as the required comparison baseline.
2. Dataset splits must hold out entire patient IDs; one patient's records must never cross training, validation, and test partitions.
3. Every feature row must have a prediction cutoff, and only records at or before that cutoff may be used. The 24-hour outcome window begins after the cutoff.
4. EHR-only and combined-stream models must be evaluated on the same held-out patients and prediction times.
5. Reports must contain metrics produced by actual held-out runs and label them as synthetic-data evaluation. They must not describe results as clinical validation.
