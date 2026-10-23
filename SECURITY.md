# Security policy

## Scope

TwinBean is a synthetic-data research prototype. Do not enter, upload, or process real patient data or protected health information.

## Reporting a vulnerability

Do not open a public issue containing a secret, credential, personal record, or exploitable security detail. Before publishing the repository, replace this line with the team's monitored private security contact:

**Security contact: TODO - add a monitored team email address**

Include the affected component, reproduction steps, expected impact, and any suggested mitigation. Remove tokens, private keys, patient information, and other sensitive material from screenshots and logs.

## Credential handling

- Store Firebase service-account files outside the repository.
- Keep `GROQ_API_KEY` and Firebase Admin credentials in `backend/.env` or the deployment secret store.
- Never place privileged values in variables prefixed with `NEXT_PUBLIC_`.
- Rotate any credential that has been committed, pasted into chat, or exposed in a screenshot.
- Treat browser Firebase configuration as application configuration, not as authorization. FastAPI must still verify every token and require `role: doctor`.

## Supported use

This hackathon prototype does not have a production support window. Security fixes should target the latest public revision. Clinical deployment is explicitly unsupported.
