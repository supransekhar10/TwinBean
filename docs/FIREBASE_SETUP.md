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

## Manual demo-account verification

1. Start the backend from `backend`:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

2. Start the frontend from `frontend` in a second terminal:

   ```powershell
   npm.cmd run dev
   ```

3. Open `http://localhost:3000`, enter the demo user's Firebase email and password, and select **Sign in**. The page must show the signed-in email. If the claim has not been assigned yet, **Check protected API** must report that the account is not approved as a doctor.

4. In a trusted backend terminal, assign the custom claim using the same demo email:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m scripts.set_doctor_role --email doctor@example.com
   ```

   The command must print that the doctor role was assigned. Only an operator with service-account access can run it. The script preserves unrelated custom claims and sets `role` to `doctor`; the browser has no role-management route.

5. Return to the signed-in browser and select **Refresh role token**. This calls Firebase `getIdToken(true)` and immediately checks the protected endpoint. Alternatively, sign out and sign back in to obtain a newly issued token.

6. Confirm the page shows **Protected API available** and **Doctor verified**. This proves `/health/authenticated` returned `200` after the backend verified the Firebase ID token and exact `role: doctor` claim.

7. Select **Sign out**. Confirm the email and protected controls disappear and the doctor sign-in form returns.

Record the date, demo email, and results in the Phase 1 verification file. Never record the password, ID token, or service-account contents.

## Expected authorization behavior

- No bearer token: `401`
- Invalid, expired, or revoked Firebase ID token: `401`
- Verified token without exactly `role: doctor`: `403`
- Verified token with `role: doctor`: `200` from `/health/authenticated`

The backend performs these checks. Frontend state is never treated as authorization.
