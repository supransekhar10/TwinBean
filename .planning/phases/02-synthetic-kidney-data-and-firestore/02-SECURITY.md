---
phase: "2"
slug: synthetic-kidney-data-and-firestore
status: verified
threats_open: 0
asvs_level: 1
created: "2026-10-04"
---

# Phase 2 - Security

## Trust Boundaries

| Boundary | Description | Data crossing |
|----------|-------------|---------------|
| Browser to FastAPI | Firebase ID token enters the protected API | Authentication and exact doctor-role claim |
| FastAPI to Firestore | Backend Admin SDK performs all patient reads | Synthetic patient summaries and separate histories |
| Seed command to Firestore | Trusted CLI stages and validates immutable cohorts | Synthetic EHR, simulated IoT, provenance, checksums |
| Staged to active cohort | One transaction publishes a validated version | Cohort ID, counts, provenance, manifest checksum |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-2-01 | Spoofing / elevation | Patient list | high | mitigate | Firebase token revocation check and exact `role: doctor`; denial precedes repository access | closed |
| T-2-02 | Information disclosure | Patient list | medium | mitigate | Typed bounded summaries only; active validated synthetic cohort only | closed |
| T-2-03 | Tampering | Cohort writes | high | mitigate | Full manifest validation, immutable versioned paths, strict readback, atomic activation | closed |
| T-2-04 | Information disclosure | Generator | high | mitigate | Explicit deterministic inputs and synthetic-only source labels; no external or real patient input | closed |
| T-2-05 | Denial of service | Seed operation | medium | mitigate | Patient, record, document, batch-write, and batch-byte bounds | closed |
| T-2-06 | Elevation | Patient detail | high | mitigate | Exact doctor dependency on detail route; rejected requests never reach storage | closed |
| T-2-07 | Information disclosure | Detail response | high | mitigate | Stable owned IDs, strict root/child provenance, typed separate streams, generic 404 | closed |
| T-2-08 | Denial of service | Detail histories | medium | mitigate | Independent 500-record caps and bounded active-cohort validation | closed |
| T-2-09 | Tampering | Live seed | high | mitigate | TwinBean-owned version namespace, set-only staging, checksum/count/link validation, transactional pointer | closed |
| T-2-10 | Information disclosure | Credentials | high | mitigate | Backend-only Admin credentials, ignored local secrets, no browser Firestore path, sanitized evidence | closed |
| T-2-11 | Elevation | Protected reads | high | mitigate | Server-side verified token with exact doctor claim on both patient endpoints | closed |
| T-2-12 | Repudiation | Verification | medium | mitigate | Sanitized timestamped evidence records command, counts, checksum, paths, HTTP results, and canary | closed |
| T-2-13 | Denial of service | Seed CLI | medium | mitigate | Explicit command only, bounded patient count, no startup seed path | closed |
| T-2-SC | Supply-chain tampering | Dependencies | high | mitigate | Phase introduced no dependency-manifest changes | closed |

## Accepted Risks Log

No accepted risks.

## Security Audit Trail

| Audit date | Threats total | Closed | Open | Evidence |
|------------|---------------|--------|------|----------|
| 2026-10-04 | 14 | 14 | 0 | Clean deep review, 39 backend tests, and post-fix live Firestore proof |

## Verification Notes

- Failed staging, validation, or activation tests preserve the previous active pointer.
- Reads resolve one active immutable cohort and reject false-like provenance, mismatched IDs, sources, versions, seeds, timestamps, counts, or checksums.
- The live rerun produced the same cohort ID and checksum twice, preserved the unrelated canary, and returned separate EHR and IoT streams through doctor-authorized endpoints.
- Credential and token material was excluded from project artifacts and command output.

## Sign-Off

- [x] All threats have a disposition.
- [x] No accepted risks require documentation.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-04
