# Firebase setup

## Create and configure the project

1. Create a Firebase project and a Web app in the Firebase console.
2. In Authentication, enable the Email/Password provider.
3. Create the demo doctor under Authentication > Users. Do not add role controls to the client.
4. Create a Cloud Firestore database for later milestones. No patient collections are required for this foundation milestone.
5. Copy the Web app configuration into `frontend/.env.local` using `frontend/.env.example` as the key list.
6. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Firebase Web configuration is public application configuration. The Admin SDK service account is privileged and must remain on the backend.

## Backend credentials

1. In Firebase project settings, create a service-account key for local development.
2. Store the downloaded JSON outside this repository.
3. Set these values in `backend/.env`:

   ```dotenv
   FIREBASE_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=C:\\secure\\path\\service-account.json
   CORS_ORIGINS=http://localhost:3000
   ```

The repository ignores local environment files and common Firebase service-account filenames. Never prefix Admin SDK values with `NEXT_PUBLIC_`.

## Approve the demo doctor

Run the trusted backend script from `backend` after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m scripts.set_doctor_role --email doctor@example.com
```

Only an operator with service-account access can run this script. It preserves unrelated custom claims and sets `role` to `doctor`; the browser has no route for changing claims.

Custom claims appear in newly issued ID tokens. After assignment, the demo user must either:

- sign out and sign back in; or
- select **Refresh role token** in TwinBean, which calls Firebase `getIdToken(true)` before checking the protected endpoint.

## Expected authorization behavior

- No bearer token: `401`
- Invalid, expired, or revoked Firebase ID token: `401`
- Verified token without exactly `role: doctor`: `403`
- Verified token with `role: doctor`: `200` from `/health/authenticated`

The backend performs these checks. Frontend state is never treated as authorization.
