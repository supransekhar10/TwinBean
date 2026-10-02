<!-- GSD:project-start source:PROJECT.md -->

## Project

**TwinBean**

TwinBean is a kidney digital twin research prototype for doctors and nephrologists. It combines synthetic longitudinal patient histories with a separate simulated IoT stream to present kidney trends, current clinical rule status, and predicted risk of a new acute kidney injury within 24 hours for adults with chronic kidney disease.

The initial product centers on a doctor dashboard ordered by predicted risk and a patient detail page. Researchers can consume model evaluation reports, but a separate researcher interface is not part of the initial prototype.

**Core Value:** Doctors can review trustworthy, clearly separated evidence about a simulated CKD patient's current state and future 24-hour AKI risk without mistaking unavailable predictions for low risk.

### Constraints

- **Data**: Use only synthetic patient and simulated IoT data — avoid handling real protected health information.
- **Security**: Verify Firebase ID tokens server-side and require `role: doctor` on protected endpoints — authentication alone is insufficient.
- **Credential handling**: Keep Firebase service-account credentials backend-only and out of Git — privileged credentials must never reach the browser or repository.
- **Authorization**: Assign custom claims only through trusted Admin SDK code — end users cannot self-elevate.
- **Database**: Use Cloud Firestore, replacing any prior SQLite plan — one authoritative persistence design avoids drift.
- **Clinical clarity**: Render clinical rules and future risk separately — clinicians must be able to distinguish observed rule state from prediction.
- **Prediction semantics**: Show prediction timestamps and missing/stale-data warnings; render invalid predictions as “Risk unavailable” — absence of a score is not zero risk.
- **Evaluation integrity**: Report actual model evaluation outputs — do not fabricate performance claims.
- **Initial delivery**: Do not implement the full clinical dashboard or ML pipeline in milestone one — establish and verify the secure application boundary first.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `$gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
