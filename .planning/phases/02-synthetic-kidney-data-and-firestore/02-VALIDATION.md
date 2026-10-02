---
phase: "2"
slug: "synthetic-kidney-data-and-firestore"
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 02-01-01 | 01 | 1 | DATA-01, DATA-02 | - | Synthetic-only deterministic generation | unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_synthetic_data.py -q` | No - W0 | pending |
| 02-02-01 | 02 | 2 | FIRE-01, DATA-03 | T-2-01 | Owned deterministic Firestore writes only | unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_patients.py -q` | No - W0 | pending |
| 02-03-01 | 03 | 3 | FIRE-05 | T-2-02 | Exact doctor-role guard on every patient route | route unit | `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_patient_routes.py -q` | No - W0 | pending |

## Wave 0 Requirements

- [ ] `backend/tests/test_synthetic_data.py` - deterministic adult CKD and separate IoT generation tests.
- [ ] `backend/tests/test_patients.py` - fake-client repository and idempotent seed-manifest tests.
- [ ] `backend/tests/test_patient_routes.py` - 401/403/200 route tests with an injected fake repository.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Firestore seed and doctor read | FIRE-01, FIRE-05, DATA-03 | Local Application Control currently blocks the `cygrpc` extension; no emulator CLI is installed | In an approved runtime, run the seed command twice, confirm unchanged deterministic document paths, then call list/detail with a refreshed doctor token. |

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies.
- [ ] Sampling continuity: no three consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Feedback latency is under 30 seconds.
- [ ] `nyquist_compliant: true` is set after implementation evidence exists.

**Approval:** pending
