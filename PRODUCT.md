# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js, TypeScript, Tailwind CSS, and Recharts on the frontend; Python FastAPI on the backend; Firebase Authentication and Cloud Firestore; scikit-learn, XGBoost, and SHAP for modeling and explanation.

## Users

Doctors and nephrologists reviewing simulated adult CKD patient histories, trends, clinical rule status, and predicted 24-hour AKI risk. Researchers consume evaluation reports, but do not have a separate interface in the initial prototype.

## Product Purpose

TwinBean is a kidney digital twin research prototype. It helps clinicians review synthetic longitudinal history and a separate simulated IoT stream without confusing current clinical rules with future risk or unavailable predictions with zero risk.

## Positioning

TwinBean combines separated evidence streams, explicit data-quality states, and time-stamped future-risk predictions in one clinician review workflow while keeping current rules, model output, and SHAP explanations distinct.

## Operating Context

The primary workflow is a doctor dashboard ordered by highest valid predicted risk, followed by a patient detail view. All monitored patients remain accessible. The prototype is evaluated locally with synthetic data and is not a clinical device.

## Capabilities and Constraints

- Firebase email/password sign-in with backend verification of ID tokens.
- Protected patient access requires the trusted custom claim `role: doctor`.
- Service-account credentials remain backend-only and out of Git.
- Invalid, missing, or stale inputs show `Risk unavailable` and warnings, never a zero-risk substitute.
- Clinical rules, predictions, prediction time, history, IoT trends, and SHAP explanations remain separate concepts.
- Evaluation uses patient-level splits, prevents future-data leakage, compares EHR-only with combined streams, and reports actual model results.

## Evidence on Hand

Only project requirements and future synthetic demonstration data are available. Do not invent clinical performance, deployment, customer, or validation claims.

## Product Principles

- Preserve clinical meaning before visual polish.
- Make authorization explicit and server-enforced.
- Expose uncertainty, missingness, and freshness honestly.
- Keep every monitored patient reachable while prioritizing valid high risk.
- Use measured model results and reproducible synthetic data.

## Accessibility & Inclusion

Use semantic controls, keyboard-visible focus, readable contrast, reduced-motion support, and text labels that do not rely on color alone.
