---
phase: "1"
slug: "secure-foundation-and-firebase-access"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-02"
---

# Phase 1 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + pytest |
| **Config file** | `frontend/vitest.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `npm.cmd --prefix frontend test -- --run && python -m pytest backend/tests -q` |
| **Full suite command** | `npm.cmd --prefix frontend run lint && npm.cmd --prefix frontend run build && python -m pytest backend/tests -q` |
| **Estimated runtime** | ~60 seconds |

## Sampling Rate

- **After every task commit:** Run the subsystem's focused tests.
- **After every plan wave:** Run the full suite.
- **Before verification:** Full suite and secret-hygiene scan must be green.
- **Max feedback latency:** 90 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | FOUND-01 | — | N/A | build | `npm.cmd --prefix frontend run build` | ❌ W0 | pending |
| 1-01-02 | 01 | 1 | FOUND-02 | — | N/A | integration | `python -m pytest backend/tests/test_health.py -q` | ❌ W0 | pending |
| 1-02-01 | 02 | 2 | AUTH-01..05 | T-1-02, T-1-03 | Reject forged and unauthorized tokens | unit/integration | `python -m pytest backend/tests/test_auth.py -q` | ❌ W0 | pending |
| 1-02-02 | 02 | 2 | AUTH-01..03, AUTH-08 | T-1-03 | Token reaches only protected route | build/unit | `npm.cmd --prefix frontend test -- --run` | ❌ W0 | pending |
| 1-03-01 | 03 | 3 | AUTH-06, AUTH-07 | T-1-04 | Role changes stay privileged | unit | `python -m pytest backend/tests/test_set_doctor_role.py -q` | ❌ W0 | pending |
| 1-03-02 | 03 | 3 | FIRE-02..04 | T-1-01 | No secret material is tracked | audit | `git grep -n "PRIVATE KEY" -- ':!*.example'` | ✅ | pending |

## Wave 0 Requirements

- [ ] Install frontend dependencies and configure Vitest.
- [ ] Install Python 3.10+ and backend development dependencies.
- [ ] Add backend test fixtures that replace Firebase token verification.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real demo doctor obtains protected health response | AUTH-06, AUTH-08, FIRE-04 | Requires user's Firebase project and account | Assign claim, force-refresh ID token, call protected health endpoint, then sign out. |

## Validation Sign-Off

- [ ] Every task has an automated verification command.
- [ ] Full suite passes locally.
- [ ] Live Firebase check is completed or explicitly documented as awaiting external configuration.
- [ ] No service-account material is tracked.
- [ ] `nyquist_compliant: true` is set after verification.

**Approval:** pending
