# Firebase and Cloud Firestore setup

## Create and configure the project

1. Create a Firebase project and a Web app in the Firebase console.
2. In Authentication, enable the Email/Password provider.
3. Create the demo doctor under Authentication > Users. Do not add role controls to the client.
4. In the same Firebase project, open **Build > Firestore Database** and create or enable the Cloud Firestore database. TwinBean uses Cloud Firestore as its only persistence authority: do not add SQLite, a browser datastore, or a browser-to-Firestore access path.
5. Copy the Web app configuration into `frontend/.env.local` using `frontend/.env.example` as the key list.
6. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Firebase Web configuration is public application configuration. The Admin SDK service account is privileged and must remain on the backend.

## Backend credentials

1. In Firebase project settings, create a service-account key for local development.
2. Store the downloaded JSON outside this repository and outside Git.
3. Set these values in `backend/.env`:

   ```dotenv
   FIREBASE_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=C:\\secure\\path\\service-account.json
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   CORS_ORIGIN_REGEX=^http://(?:localhost|127\.0\.0\.1|192\.168(?:\.\d{1,3}){2}):300[01]$
   ```

The repository ignores local environment files and common Firebase service-account filenames. Never prefix Admin SDK values with `NEXT_PUBLIC_`, put service-account material in browser configuration, or record a credential path in operational evidence.

## Seed the deterministic synthetic cohort

Run this command explicitly from `backend` after Cloud Firestore is enabled and Application Default Credentials are available to the backend process:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_synthetic_data --seed 2402 --generator-version phase2-v1 --time-basis 2026-01-01T00:00:00+00:00 --patient-count 12
```

This is a privileged, backend-only operation. It is never run during FastAPI startup, from the browser, or by browser code. The command uses the existing backend Firebase Admin application and Application Default Credentials.

For identical seed, generator version, UTC time basis, and patient count, the generated cohort ID and manifest checksum are immutable and deterministic. A seed first stages records only under one TwinBean-owned version, reads that version back, validates its counts, links, UTC timestamps, exact provenance, and checksum, then atomically changes this one metadata pointer:

- `twinbean_cohorts/{cohort_id}` (validated cohort descriptor)
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/ehr_events/{event_id}`
- `twinbean_cohorts/{cohort_id}/patients/{patient_id}/iot_observations/{observation_id}`
- `twinbean_metadata/active_cohort` (the only active-cohort pointer)

The seed never writes a global `patients` collection, deletes or resets a collection, or mutates unrelated Firestore documents. It preserves prior versions; failed staging, readback validation, or pointer activation leaves the prior active version unchanged. Before live verification, create an unrelated canary outside `twinbean_cohorts` and `twinbean_metadata` and compare its non-secret payload hash before and after two identical seed runs.

Each generated patient produces one root, 26 EHR events, and 24 IoT observations: 51 staged documents per patient. At the supported maximum of 100 patients, a run stages 5,100 clinical documents plus one cohort descriptor, then performs one active-pointer transaction: **5,102 writes total**, split into Firestore batches of at most 100 staged writes.

## Doctor-only patient read verification

1. Start FastAPI from `backend`:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0
   ```

2. In a trusted backend terminal, assign the demo account its custom claim. Only an operator with backend service-account access can do this:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.set_doctor_role --email doctor@example.com
   ```

3. Refresh the Firebase ID token after claim assignment (use `getIdToken(true)` in the signed-in client, or sign out and sign back in). The refreshed token must carry the exact `role: doctor` custom claim.
4. Send that bearer token only to FastAPI, never directly to Firestore. Call `GET /patients` and expect HTTP `200` with a bounded synthetic root list.
5. Choose one returned `tbp-...` ID and call `GET /patients/{patient_id}` with the same refreshed token. Expect HTTP `200` and separately named `ehr_history` and `iot_observations` response fields; do not treat the two source streams as one data source.
6. Verify that a Firebase-verified token without exactly `role: doctor` receives `403`. Do not use frontend state as authorization.

No bearer token, password, service-account JSON, private key, or credential path may be pasted into commands, logs, screenshots, or the live-evidence file. Record only sanitized timestamps, checksums, counts, representative owned paths, HTTP statuses, response-shape notes, and operator approval.

## Verification expectations

Before a public demonstration, repeat the deterministic seed in the intended Firebase project, read back both streams, confirm that an unrelated canary document remains unchanged, and verify the protected doctor routes. Record only sanitized counts, timestamps, checksums, representative owned paths, and HTTP status codes. Do not publish credentials, tokens, private project identifiers, or patient-like personal information.

## Expected authorization behavior

- No bearer token: `401`
- Invalid, expired, or revoked Firebase ID token: `401`
- Verified token without exactly `role: doctor`: `403`
- Verified token with exact `role: doctor`: `200` from `GET /patients` and `GET /patients/{patient_id}` when the requested synthetic patient exists

FastAPI performs these checks. Browser state is never treated as authorization, and browser code never queries Firestore directly.
