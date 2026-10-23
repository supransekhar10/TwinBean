# TwinBean project brief

TwinBean is a kidney digital twin research prototype for doctors and nephrologists. It combines deterministic synthetic longitudinal EHR histories with a separate simulated medical-IoT stream to present kidney trends, current clinical rule status, and predicted risk of a new acute kidney injury within 24 hours for adults with chronic kidney disease.

The primary workflow is a doctor dashboard ordered by current review priority and valid predicted risk, followed by a patient detail view. The interface keeps observed rules, future model output, missing-data warnings, SHAP explanations, and doctor-authored notes separate.

## Safety constraints

- Use only synthetic patient and simulated IoT data.
- Verify Firebase ID tokens server-side and require the exact custom claim `role: doctor` on protected endpoints.
- Keep Firebase service-account credentials and AI-provider keys backend-only and outside Git.
- Render invalid predictions as `Risk unavailable`; absence of a score is never zero risk.
- Show prediction timestamps and missing or stale-data warnings.
- Report measured synthetic evaluation results without claiming clinical validation.
- Treat Twini output as educational assistance, not diagnosis or treatment guidance.
