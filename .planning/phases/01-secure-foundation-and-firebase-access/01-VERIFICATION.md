---
phase: 01-secure-foundation-and-firebase-access
status: human_needed
verified: 2026-10-03
---

# Phase 1 Verification

## Automated verdict

PASS. The affected frontend lint, Vitest, and production-build checks pass. The existing seven backend tests pass, npm reports zero vulnerabilities, and local runtime probes confirm public `200` and unauthenticated protected `401` behavior.

## Responsive layout result

PASS on 2026-10-03 using Playwright Core with installed Microsoft Edge against the production Next.js server.

| Viewport | Document width | Client width | Targeted overflow |
|----------|----------------|--------------|-------------------|
| 390 x 844 | 390 px | 390 px | None |
| 1440 x 1000 | 1440 px | 1440 px | None |

The test measured `.page-shell`, the product header and prototype label, content grid, introduction, lede, authentication panel, and footer. Every target remained within its viewport and reported no internal horizontal overflow. Screenshots were refreshed at `.impeccable/review/mobile.png` and `.impeccable/review/desktop.png`.

## Security evidence

- Firebase Admin verifies tokens with revocation checking.
- Protected access requires the exact decoded claim `role: doctor`.
- Role assignment exists only in the trusted backend script and preserves unrelated claims.
- Local environment files and common service-account key names are ignored and untracked.

## Human verification remaining

The live Firebase demo-account flow has not yet been reported as passed. Follow `docs/FIREBASE_SETUP.md`: sign in, confirm pre-approval denial if applicable, assign `role: doctor` through the trusted backend script, force-refresh the ID token, confirm **Protected API available** and **Doctor verified**, then sign out.

Phase 1 remains open until that real-account result is recorded. Do not record the password, ID token, or service-account contents.
