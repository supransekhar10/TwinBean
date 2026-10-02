---
phase: "1"
slug: "secure-foundation-and-firebase-access"
status: verified-automated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-02"
updated: "2026-10-02"
---

# Phase 1 Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | Vitest + pytest |
| Config files | `frontend/vitest.config.mts`, `backend/pyproject.toml` |
| Frontend command | `npm.cmd run lint; npm.cmd test; npm.cmd run build` |
| Backend command | `.\\.venv\\Scripts\\python.exe -m pytest` |

## Verification Results

| Area | Result | Evidence |
|------|--------|----------|
| Frontend lint | Pass | No warnings or errors |
| Frontend tests | Pass | 2 tests |
| Frontend production build | Pass | Next.js static route generated |
| Backend tests | Pass | 7 tests |
| Dependency audit | Pass | 0 vulnerabilities |
| Local runtime | Pass | Public health `200`; protected route without token `401` |
| Secret hygiene | Pass | Local env files and credential patterns ignored; no tracked private key |
| Live Firebase doctor flow | Manual pending | Requires the user's demo account credentials |

## Requirement and Threat Coverage

- Foundation and configuration: frontend build, backend liveness, explicit CORS, environment examples.
- T-1-01: privileged files remain backend-only and ignored.
- T-1-02: missing, invalid, and expired-token paths normalize to `401`.
- T-1-03: verified non-doctor tokens receive `403`; exact doctor role succeeds.
- T-1-04: only the trusted backend script assigns the role and preserves other claims.
- T-1-05: browser origins use an explicit allowlist.

## Sign-Off

Automated validation is complete. Live Firebase sign-in and the real doctor-token response remain an explicit manual verification, documented in `docs/FIREBASE_SETUP.md`.
