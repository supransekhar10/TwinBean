---
phase: "1"
status: complete
researched: "2026-10-02"
confidence: high
---

# Phase 1 Research — Secure Foundation and Firebase Access

## Scope

Research only the unresolved implementation details for Firebase email/password sign-in, ID-token verification, doctor custom claims, local credentials, browser-to-FastAPI requests, and verification. Dashboard, Firestore patient data, IoT, and ML work remain deferred.

## Findings

### Browser authentication

- Use Firebase's modular Web SDK with `signInWithEmailAndPassword`, `signOut`, and an auth-state observer.
- Send the signed-in user's Firebase ID token as `Authorization: Bearer <token>` to FastAPI.
- After assigning a custom claim, force a fresh token with `currentUser.getIdToken(true)` or sign in again; an already issued token does not gain the claim automatically.
- Firebase client configuration is public application metadata and belongs in `NEXT_PUBLIC_FIREBASE_*` variables; service-account material must never use a public prefix.

### Backend authorization

- Initialize the Python Admin SDK with Application Default Credentials. For local service-account use, set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON file path rather than loading or embedding its contents in application code.
- Use `firebase_admin.auth.verify_id_token()` on the bearer token. Treat verification failure as `401 Unauthorized`.
- Check the decoded token's `role` claim for the exact value `doctor`; a verified user without that claim receives `403 Forbidden`.
- Assign the role only through a backend-only script using `set_custom_user_claims`. Preserve existing claims when adding the role because the setter replaces the custom-claims object.

### Local frontend/backend integration

- Configure FastAPI CORS with an explicit frontend origin; wildcard origins are unsuitable for browser requests carrying authorization headers.
- Keep a public unprotected liveness route and a separate protected health route so local process health can be distinguished from authorization health.
- Unit-test token failure and role enforcement by injecting or monkeypatching the token verifier. Live Firebase verification remains a documented manual check because it requires the user's project and demo account.

## Recommended Structure

```text
frontend/                 Next.js App Router application
  src/app/                sign-in and authenticated health UI
  src/components/         auth/health client component
  src/lib/                Firebase client and backend API helper
backend/
  app/main.py             FastAPI application and routes
  app/auth.py             bearer extraction, token verification, doctor guard
  app/firebase.py         idempotent Admin SDK initialization
  scripts/set_doctor_role.py
  tests/                  pytest authorization and route tests
```

## Validation Architecture

- Frontend: ESLint, TypeScript/Next production build, and Vitest tests for API/error-state logic.
- Backend: pytest with FastAPI TestClient and monkeypatched Firebase verification.
- Security checks: missing bearer token → 401; invalid token → 401; valid non-doctor token → 403; valid doctor token → 200.
- Secret hygiene: Git ignore rules plus a tracked-file scan for `.env`, service-account JSON, and private-key markers.
- Manual Firebase check: assign claim, force-refresh token, invoke protected endpoint, sign out, confirm access is removed.

## Sources

- [Firebase password authentication for Web](https://firebase.google.com/docs/auth/web/password-auth)
- [Firebase ID-token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [Firebase custom claims](https://firebase.google.com/docs/auth/admin/custom-claims)
- [Firebase Admin SDK setup](https://firebase.google.com/docs/admin/setup)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Next.js environment variables](https://nextjs.org/docs/app/guides/environment-variables)

## RESEARCH COMPLETE

Phase 1 can be planned without broader ecosystem research.
