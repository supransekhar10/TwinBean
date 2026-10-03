# Phase 2: Synthetic Kidney Data and Firestore - Pattern Map

**Mapped:** 2026-10-03  
**Files analyzed:** 10  
**Analogs found:** 7 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/firestore.py` | service | request-response | `backend/app/firebase.py` | role-match |
| `backend/app/synthetic_data.py` | model | transform | — | no analog |
| `backend/app/patients.py` | service | CRUD | — | no analog |
| `backend/app/patient_routes.py` | route | request-response | `backend/app/main.py` + `backend/app/auth.py` | role/data-flow match |
| `backend/app/main.py` | config | request-response | `backend/app/main.py` | exact (modify in place) |
| `backend/scripts/seed_synthetic_data.py` | utility | batch | `backend/scripts/set_doctor_role.py` | role-match |
| `backend/tests/test_synthetic_data.py` | test | transform | — | no analog |
| `backend/tests/test_patients.py` | test | CRUD | `backend/tests/test_set_doctor_role.py` | partial |
| `backend/tests/test_patient_routes.py` | test | request-response | `backend/tests/test_auth.py` | exact |
| `docs/FIREBASE_SETUP.md` | config | request-response | `docs/FIREBASE_SETUP.md` | exact (modify in place) |

## Pattern Assignments

### `backend/app/firestore.py` (service, request-response)

**Analog:** `backend/app/firebase.py` (tracked; lines 1-18)

Keep all Admin SDK initialization in the existing factory; the Firestore seam imports and reuses it rather than initializing another app.

```python
import firebase_admin
from firebase_admin import credentials

from .settings import get_settings

def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        return firebase_admin.initialize_app(credentials.ApplicationDefault(), options)
```

Use `firebase_admin.firestore.client(app=get_firebase_app())` in the new module. Do not introduce credentials, browser configuration, or another initializer.

---

### `backend/app/synthetic_data.py` (model, transform)

**Analog:** none. This is the first typed, deterministic data generator.

Use the research contract: pure typed models and `generate_cohort(seed, generator_version, time_basis)` with no Firebase imports. Generate stable IDs, adult CKD histories, separate EHR and IoT records, source metadata, UTC timestamps, and explicit synthetic/provenance fields. Keep clinical rules and predictions out of these models.

---

### `backend/app/patients.py` (service, CRUD)

**Analog:** none. This is the first persistence repository.

Follow the import/factory boundary in `backend/app/firebase.py`; accept a Firestore client at the repository seam so tests can use a fake. Persist only deterministic TwinBean-owned paths:

```text
patients/{patient_id}
patients/{patient_id}/ehr_events/{event_id}
patients/{patient_id}/iot_observations/{event_id}
```

List reads must load root summaries only. Detail reads query both event collections independently and return distinct `ehr_history` and `iot_observations` values. Batch writes use explicit document IDs and `set()` only; never implement a collection-wide delete/reset path.

---

### `backend/app/patient_routes.py` (route, request-response)

**Analogs:** `backend/app/main.py` (tracked; lines 1-32), `backend/app/auth.py` (tracked; lines 1-42)

**Imports/dependency pattern** (`backend/app/main.py`, lines 1-7):

```python
from typing import Any

from fastapi import Depends, FastAPI

from .auth import require_doctor
```

**Authorization pattern — copy unchanged** (`backend/app/auth.py`, lines 16-42):

```python
def require_doctor(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A Firebase ID token is required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = verify_firebase_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The Firebase ID token is invalid or expired.", headers={"WWW-Authenticate": "Bearer"}) from exc
    if claims.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access is required.")
    return claims
```

Every patient list/detail handler must declare `Depends(require_doctor)` before repository access. Use typed path/query/response models; do not leak Firestore objects. Preserve separate named output fields for EHR and IoT data.

---

### `backend/app/main.py` (config, request-response)

**Analog:** `backend/app/main.py` (tracked; lines 9-32)

Add the patient router to the existing application without changing the CORS policy or health-route behavior.

```python
settings = get_settings()
app = FastAPI(title="TwinBean API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/health/live")
def public_health() -> dict[str, str]:
    return {"service": "twinbean-api", "status": "ok"}
```

Mount routes additively. The existing authenticated health endpoint remains a regression sentinel for the doctor guard.

---

### `backend/scripts/seed_synthetic_data.py` (utility, batch)

**Analog:** `backend/scripts/set_doctor_role.py` (tracked; lines 1-35)

**CLI and backend-only Admin pattern:**

```python
import argparse

from app.firebase import get_firebase_app

def main() -> None:
    parser = argparse.ArgumentParser(description="Assign TwinBean's trusted doctor custom claim.")
    parser.add_argument("--email", required=True, help="Existing Firebase user email")
    args = parser.parse_args()
    uid = assign_doctor_role(args.email)
    print(f"Doctor role assigned to {args.email} ({uid}).")

if __name__ == "__main__":
    main()
```

Use a similarly explicit command (`--seed`, version/time options as chosen) that calls the pure generator then repository batch writer. It must never run from API startup and must print non-sensitive seed/manifest results only.

---

### `backend/tests/test_synthetic_data.py` (test, transform)

**Analog:** none for generators. Use the project’s direct pure-function assertion style from `backend/tests/test_set_doctor_role.py` (tracked; lines 1-12):

```python
from scripts.set_doctor_role import with_doctor_role

def test_doctor_role_preserves_unrelated_claims() -> None:
    assert with_doctor_role({"tenant": "demo"}) == {"tenant": "demo", "role": "doctor"}
```

Test same-input determinism, adult/CKD constraints, provenance, stable IDs, and that EHR and IoT values are produced as distinct typed streams. Do not use Firebase in these tests.

---

### `backend/tests/test_patients.py` (test, CRUD)

**Analog:** `backend/tests/test_set_doctor_role.py` (tracked; lines 1-12), partial match.

Keep repository tests unit-level with fake Firestore client/batch/document objects. Assert explicit deterministic paths, owned-doc `set()` writes, idempotent reruns, root-only list queries, and independently returned EHR/IoT histories. No live Firestore test dependency.

---

### `backend/tests/test_patient_routes.py` (test, request-response)

**Analog:** `backend/tests/test_auth.py` (tracked; lines 1-54)

**App/TestClient and auth monkeypatch pattern** (lines 1-23):

```python
from fastapi.testclient import TestClient
import pytest

from app import auth as auth_module
from app.main import app

client = TestClient(app)

monkeypatch.setattr(
    auth_module,
    "verify_firebase_token",
    lambda _token: {"uid": "demo-doctor", "role": "doctor"},
)
response = client.get(
    "/health/authenticated",
    headers={"Authorization": "Bearer valid-token"},
)
assert response.status_code == 200
```

Apply the same token seam to both patient endpoints, override/inject a fake repository, and cover `401` missing/invalid token, `403` non-doctor, and doctor `200`. Assert detail responses have separate `ehr_history` and `iot_observations` fields.

---

### `docs/FIREBASE_SETUP.md` (config, request-response)

**Analog:** `docs/FIREBASE_SETUP.md` (tracked; lines 1-67)

Extend its numbered, executable operational instructions. Its credential boundary must remain intact:

```markdown
The Admin SDK service account is privileged and must remain on the backend.
...
Store the downloaded JSON outside this repository.
...
Never prefix Admin SDK values with `NEXT_PUBLIC_`.
```

Document Firestore enablement, the explicit seed command, and doctor-token patient-read verification. Do not document browser Firestore access or secrets.

## Shared Patterns

### Firebase initialization
**Source:** `backend/app/firebase.py` (tracked; lines 1-18)  
**Apply to:** `firestore.py`, repository/seed operations

One process-wide `get_firebase_app()` owns Application Default Credentials and optional project configuration. All Firestore access derives from it.

### Doctor authorization
**Source:** `backend/app/auth.py` (tracked; lines 16-42)  
**Apply to:** every patient data route

Use the unchanged `require_doctor` FastAPI dependency. It validates a bearer Firebase token with revocation checking and permits only an exact `role == "doctor"` claim.

### Offline Firebase-boundary tests
**Source:** `backend/tests/test_auth.py` (tracked; lines 1-54)  
**Apply to:** `test_patient_routes.py`

Monkeypatch `auth_module.verify_firebase_token`; repositories additionally receive fakes. Tests must not depend on live Firestore, particularly while the local Firestore gRPC import is unavailable.

### Backend-only operational commands
**Source:** `backend/scripts/set_doctor_role.py` (tracked; lines 1-35)  
**Apply to:** `seed_synthetic_data.py`

Use `argparse`, direct `main()`, `if __name__ == "__main__"`, and the server-only Admin app boundary. Never seed on FastAPI startup.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/app/synthetic_data.py` | model | transform | No prior synthetic generators or domain models exist. |
| `backend/app/patients.py` | service | CRUD | No persistence repository exists; Firestore is new in this phase. |
| `backend/tests/test_synthetic_data.py` | test | transform | No generator test suite exists. |

## Metadata

**Analog search scope:** `backend/app`, `backend/scripts`, `backend/tests`, `docs`, backend package config  
**Files scanned:** 10  
**Pattern extraction date:** 2026-10-03
