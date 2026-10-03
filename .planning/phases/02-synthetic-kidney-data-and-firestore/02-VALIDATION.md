---
phase: "2"
slug: "synthetic-kidney-data-and-firestore"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-03"
---

# Phase 2 - Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_synthetic_data.py backend/tests/test_patients.py backend/tests/test_patient_routes.py -q` |
| **Full suite command** | `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` |
| **Estimated runtime** | under 30 seconds |

## Sampling Rate

- **After every task commit:** Run the focused tests for the changed module.
- **After every plan wave:** Run the full backend suite.
- **Before `$gsd-verify-work`:** Full backend suite must be green.
- **Max feedback latency:** 30 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | FIRE-01, FIRE-05 | T-2-01, T-2-02 | Lazy Admin-client boundary; exact-doctor list tracer; bounded root summaries | route/repository unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_patient_routes.py backend/tests/test_auth.py backend/tests/test_health.py -q` | Yes | green |
| 02-01-02 | 01 | 1 | FIRE-05 | T-2-01 | 401/403/200 semantics, denial before repository access, and bounded limits | route unit + regression | `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` | Yes | green |
| 02-02-01 | 02 | 2 | DATA-01, DATA-02 | T-2-04 | Deterministic adult CKD generation, synthetic provenance, and distinct IoT types | pure unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_synthetic_data.py -q` | Yes | green |
| 02-02-02 | 02 | 2 | FIRE-01, DATA-02, DATA-03 | T-2-03, T-2-05 | Deterministic owned `set()` paths, same-input idempotency, no delete/reset, and size bounds | repository unit + regression | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_synthetic_data.py backend/tests/test_patients.py backend/tests -q` | Yes | green |
| 02-03-01 | 03 | 3 | FIRE-05, DATA-02, DATA-03 | T-2-06, T-2-07, T-2-08 | Exact-doctor detail route with independent bounded EHR and IoT queries | route/repository unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_patients.py backend/tests/test_patient_routes.py -q` | Yes | green |
| 02-03-02 | 03 | 3 | FIRE-05, DATA-02, DATA-03 | T-2-06, T-2-07, T-2-08 | Safe 404, empty-stream, independent ordering, and full regression behavior | route/repository unit + regression | `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` | Yes | green |
| 02-04-01 | 04 | 4 | FIRE-01, FIRE-05, DATA-03 | T-2-09, T-2-10, T-2-11 | Firestore operations guide documents exact backend-only seeding, owned-path idempotency, credential boundaries, and protected reads | documentation/source contract + approved-runtime evidence | See `02-04-LIVE-EVIDENCE.md` and `docs/FIREBASE_SETUP.md` contract check | Yes | green |

## Wave 0 Requirements

- [x] `backend/tests/test_synthetic_data.py` - deterministic adult CKD and separate IoT generation tests.
- [x] `backend/tests/test_patients.py` - fake-client repository and idempotent seed-manifest tests.
- [x] `backend/tests/test_patient_routes.py` - 401/403/200 route tests with an injected fake repository.

## Approved-Runtime Verification

| Behavior | Requirement | Evidence | Status |
|----------|-------------|----------|--------|
| Live Firestore seed and doctor read | FIRE-01, FIRE-05, DATA-03 | Versioned repeat-seed, activation, readback, unrelated-canary, and protected-route results in `02-04-POST-FIX-LIVE-EVIDENCE.md` | Passed |

## Validation Sign-Off

- [x] All tasks have automated verification or approved-runtime evidence.
- [x] Sampling continuity: no three consecutive tasks without automated verification.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency is under 30 seconds.
- [x] `nyquist_compliant: true` is set from observed evidence.

**Approval:** validated

## Validation Audit 2026-10-03

| Metric | Count |
|--------|-------|
| Requirements audited | 5 |
| Covered | 5 |
| Partial | 0 |
| Missing | 0 |
| New gaps found | 0 |
| Escalated | 0 |

FIRE-01, FIRE-05, DATA-01, DATA-02, and DATA-03 are **COVERED**.

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` - 39 passed.
- Plan 02-04 PowerShell documentation/source contract command - passed.
- `02-04-POST-FIX-LIVE-EVIDENCE.md` records sanitized versioned staging, activation, repeat-seed, unrelated-canary, and exact-doctor read evidence.
- Failure-path tests cover inactive partial writes, validation mismatch, activation failure, strict provenance, cohort isolation, and child ownership.
