# TwinBean

TwinBean is a synthetic-data kidney digital twin research prototype for doctors and nephrologists. It provides Firebase doctor access, a risk-ranked dashboard, patient-level EHR and simulated IoT trends, separated clinical-rule and future-risk results, SHAP explanations, and reproducible synthetic model evaluation.

Not for clinical use. Do not use real patient data.

## Local setup

1. Follow [Firebase setup](docs/FIREBASE_SETUP.md).
2. Copy `frontend/.env.example` to `frontend/.env.local` and fill in the browser Firebase values.
3. Copy `backend/.env.example` to `backend/.env`, set the Firebase project ID, and point `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON file outside the repository.
4. Install and start the frontend:

   ```powershell
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```

5. In a second terminal, install and start the backend:

   ```powershell
   cd backend
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

Open `http://localhost:3000`. The public API health check is `http://localhost:8000/health/live`; `/health/authenticated` requires a current Firebase ID token with `role: doctor`.

The dashboard loads only after the protected doctor health check succeeds. Patient pages reuse doctor-protected backend endpoints; Firebase service credentials remain backend-only.

## Synthetic model evaluation

Run the actual patient-level, time-safe EHR-only versus combined-stream comparison:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.evaluate_models
```

Results are written to `backend/artifacts/evals/phase6-model-evaluation.json` and `docs/MODEL_EVALUATION.md`. These are synthetic-data research results, not clinical validation.

## Verification

```powershell
cd frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build

cd ..\backend
.\.venv\Scripts\python.exe -m pytest
```
