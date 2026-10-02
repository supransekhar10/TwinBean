# API Coverage — Firebase Authentication and Admin SDK

> Full coverage by default for the Phase 1 integration surface. Opt-outs are explicit.

| capability | decision | reason |
|---|---|---|
| email/password sign-in | INTEGRATE | |
| browser sign-out | INTEGRATE | |
| auth-state observation | INTEGRATE | |
| ID-token retrieval and forced refresh | INTEGRATE | |
| Admin SDK initialization | INTEGRATE | |
| ID-token verification | INTEGRATE | |
| lookup user by email | INTEGRATE | |
| read existing custom claims | INTEGRATE | |
| set `role: doctor` custom claim | INTEGRATE | |
| account registration UI | OPT-OUT | Demo accounts are created through Firebase Console for the prototype. |
| password reset UI | OPT-OUT | Deferred beyond the Phase 1 secure skeleton. |
| email verification enforcement | OPT-OUT | Not required by the agreed prototype scope. |
| OAuth providers | OPT-OUT | Email/password is the agreed provider. |
| token revocation checks on every request | OPT-OUT | Standard signature/expiry verification is sufficient for this prototype phase. |
| Firestore patient operations | OPT-OUT | Explicitly assigned to Phase 2. |
