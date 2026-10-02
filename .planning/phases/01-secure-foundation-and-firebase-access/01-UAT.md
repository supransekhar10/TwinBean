---
status: partial
phase: 01-secure-foundation-and-firebase-access
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
started: 2026-10-03T00:14:51+05:30
updated: 2026-10-03T00:14:51+05:30
---

# Phase 1 UAT

## Current Test

number: 3
name: Live Firebase doctor flow
expected: |
  The demo user signs in, receives the trusted doctor claim, refreshes the ID token, reaches the protected API, and signs out.
awaiting: user response

## Tests

### 1. Responsive authentication shell
expected: The sign-in screen fits at 390 x 844 and 1440 x 1000 without horizontal clipping or hidden content.
result: pass
source: automated Playwright/Edge measurement and screenshots

### 2. Automated authentication boundary
expected: Missing or invalid tokens return 401, non-doctor tokens return 403, and a verified doctor token reaches the protected health response.
result: pass
source: seven passing backend tests plus two passing frontend request tests

### 3. Live Firebase doctor flow
expected: The configured demo user signs in, receives `role: doctor` from the trusted script, refreshes the token, sees protected access succeed, and signs out.
result: blocked
blocked_by: third-party
reason: Requires the user's Firebase demo-account credentials and interactive confirmation.

## Summary

total: 3
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps

None. The remaining item is an external manual verification, not an implementation gap.
