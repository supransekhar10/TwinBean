---
phase: 03-clinical-rules-and-aki-prediction
status: secured
asvs_level: 1
threats_closed: 17
threats_open: 0
verified: 2026-10-05
---

# Phase 03 Security Verification

## Verdict

SECURED — all 17 unique threats and all 22 declared plan entries are mitigated.

## Verified Controls

- Exact Firebase doctor-role authorization precedes prediction and result-history access.
- Active synthetic-cohort ownership and provenance are validated before reads or writes.
- Clinical rules and predictions use separate validated schemas and Firestore collections.
- Clinical result writes use transactional reads-before-writes; serial and concurrent retries return immutable evidence without overwriting it.
- Invalid, missing, stale, future-dated, artifact-invalid, or SHAP-invalid inputs produce unavailable results without a probability.
- Feature construction enforces cutoff safety, an explicit allowlist, provenance, units, freshness, and forbidden-field rejection.
- Model loading verifies server-selected paths, manifest/schema/package versions, and member checksums before deserialization.
- SHAP explanations verify feature alignment, finite values, additivity, and raw-margin reconciliation.
- Evaluation manifests contain actual digests and failures, reject unsupported claims and sensitive patterns, and remain synthetic-research-only.
- Exact ML dependency pins and provenance checks pass; tracked credential and private-key patterns were not found.

## Verification Results

- 12 focused authorization, retry, concurrency, transaction, and cutoff-safety checks passed.
- Exact pandas, scikit-learn, XGBoost, and SHAP versions matched; pip check passed.
- Checked-in model artifact hashes matched the manifest and verified inference succeeded.
- The checked-in evaluation manifest passed verification.
- No unregistered threat flags remain.

## Live-Evidence Boundary

Phase 03 clinical endpoints were not claimed as live-tested against Firebase. Live claims remain limited to the existing Phase 1 doctor-auth evidence and Phase 2 protected Firestore evidence.
