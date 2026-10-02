# Phase 2: Synthetic Kidney Data and Firestore - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-10-03
**Phase:** 2-Synthetic Kidney Data and Firestore
**Areas discussed:** Synthetic cohort contract, EHR and IoT separation, Firestore seeding and provenance, Doctor-only read surface

---

## Synthetic Cohort Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Versioned deterministic generator | Fixed configurable seed, stable IDs, and recorded provenance | Yes |
| Static fixture bundle | Reproducible but less useful for cohort variation | |
| Fresh random cohort | New untraceable data on every run | |

**Choice:** Versioned deterministic generator (recommended default selected in auto mode).

## EHR and IoT Separation

| Option | Description | Selected |
|--------|-------------|----------|
| Separate typed streams | Independent collections, timestamps, and source metadata | Yes |
| Combined event stream | One collection differentiated only by event type | |
| Embedded arrays | All observations inside patient documents | |

**Choice:** Separate typed streams (recommended default selected in auto mode).

## Firestore Seeding and Provenance

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit idempotent seed command | Controlled, repeatable, and preserves unrelated documents | Yes |
| Startup seeding | Mutates data whenever the API starts | |
| Manual console entry | Not reproducible | |

**Choice:** Explicit idempotent seed command (recommended default selected in auto mode).

## Doctor-Only Read Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Protected backend API only | Reuses verified doctor authorization and keeps Admin SDK server-side | Yes |
| Direct browser reads | Requires a second authorization boundary | |
| Mixed access | Creates inconsistent enforcement | |

**Choice:** Protected backend API only (recommended default selected in auto mode).

## Codex's Discretion

- Prototype cohort size, observation cadence, exact field bounds, small-dataset pagination, and internal module layout.

## Deferred Ideas

- Phase 3 owns clinical rules, AKI prediction, availability semantics, and SHAP.
- Phases 4 and 5 own dashboard and patient-detail presentation.
