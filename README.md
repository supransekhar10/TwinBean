# TwinBean

TwinBean is a synthetic-data kidney digital twin research prototype for doctors and nephrologists. This milestone provides the Next.js and FastAPI skeletons, Firebase email/password sign-in, doctor-claim authorization, and public/protected health checks.

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

## Verification

```powershell
cd frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build

cd ..\backend
.\.venv\Scripts\python.exe -m pytest
```
