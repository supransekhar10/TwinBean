---
phase: "04"
slug: "risk-ranked-doctor-dashboard"
status: draft
shadcn_initialized: false
preset: none
created: "2026-10-05"
---

# Phase 04 â€” UI Design Contract

> Visual and interaction contract for the Risk-Ranked Doctor Dashboard. It preserves clinical meaning, doctor-only access, and the Phase 3 prediction union.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none â€” reuse existing Tailwind 4 utilities and `frontend/src/app/globals.css` tokens |
| Preset | not applicable; no `components.json` is present |
| Component library | none |
| Icon library | none installed; use text labels until a single verified icon package is deliberately added |
| Font | Aptos, `Segoe UI Variable`, `Segoe UI`, sans-serif |

The dashboard must use the existing light clinical palette and visible 3px `--focus` outline. It must use a solid `--paper` canvas: no gradient, transparency treatment, glassmorphism, purple, or decorative illustration.

## Product and Data Contract

- Persistent product bar: TwinBean wordmark, `Research prototype / synthetic data only`, signed-in doctor email when available, and `Sign out`.
- Main heading: `Patient risk overview`. Supporting text: `All monitored synthetic patients. Valid 24-hour AKI risks appear first.`
- Source only an authorised, bounded server-side dashboard projection. It contains patient identity (`patient_id`, display name, age, CKD stage), latest current-rule summary, latest prediction summary, generated time, and trusted warning/reason codes.
- The backend, not the browser, marks a prediction `available` or `unavailable`, selects its latest stored result, and orders the list: available predictions descending by probability, then unavailable predictions, then display name ascending as a stable tie-breaker.
- An available forecast displays `24-hour AKI risk` followed by its percentage and `Prediction generated {local date and time}`. A forecast must never show a severity tier, clinical threshold, or treatment implication unless a later evidence-backed requirement adds one.
- An unavailable forecast displays exactly `Risk unavailable`; it never displays `0%`, an empty percent sign, a progress bar, or a risk color. Show its mapped data-quality warning/reason immediately below it before the patient navigation control.
- Current-rule status has its own `Current clinical rule` label and plain-language status mapping: `Criteria met`, `Criteria not met`, or `Insufficient creatinine history`. It must remain visually separated from the future-risk region with its own label, DOM grouping, and accessible name.
- Do not render raw API error payloads, raw reason-code identifiers, credentials, tokens, or untrusted model/version strings. Map the finite trusted reason/warning enum to concise copy; unknown values use `Prediction data needs review.`

## Layout and Content Hierarchy

### Desktop â€” 1024px and wider

- Use a centred `max-width: 1280px` content region with 24px horizontal page padding and 32px between the heading block and dashboard list.
- Use a full-width, semantic `<table>` with caption `Risk-prioritized monitored patients`. Keep a visually visible column heading for every field; do not rely on a legend or tooltip for essential meaning.
- Columns, in this order: Patient; Current clinical rule; 24-hour AKI risk; Prediction generated; Data quality; Open.
- Patient cell: display name first, then `Age {age} Â· CKD stage {stage}`. The exact synthetic-only label remains page-level, not repeated in every row.
- The `24-hour AKI risk` cell is the highest-scan-priority cell and carries the probability or exact unavailable label. The current-rule cell must not visually compete with it through equivalent accent treatment.
- `Data quality` is blank only when the returned summary has no warning/reason. When present, it shows a labelled warning block with text; it never uses an icon or color without text.
- Row separators use 1px `--line`; avoid a card-per-row layout at density 6. A row gets a subtle `--accent-soft` background on pointer hover only, never a risk-severity fill.

### Mobile â€” 390px to 639px

- Retain the product bar, heading, order explanation, and patient count. Stack header controls without horizontal scrolling.
- Replace the table with a semantic ordered list of patient cards. Each card has 16px padding, 16px internal gaps, and a 1px `--line` border; do not preserve desktop columns with sideways scrolling.
- Card order is Patient; `24-hour AKI risk`; prediction generation time; `Data quality`; `Current clinical rule`; `Open patient`.
- Each label stays visible above or beside its value. The `Open patient` control spans the card width and has a 44px minimum height.
- Use `min-width: 0`, `overflow-wrap: anywhere` for names and warning text, and `font-variant-numeric: tabular-nums` for risk percentages and timestamps. The document width must remain at or below the 390px viewport width.

## Spacing Scale

Declared values (all multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Label-to-value and inline icon gaps |
| sm | 8px | Compact metadata and badge gaps |
| md | 16px | Card padding, cell internals, default control spacing |
| lg | 24px | Page padding and heading-to-list gap |
| xl | 32px | Major dashboard region gap |
| 2xl | 48px | Desktop page-top space |
| 3xl | 64px | Not used in the high-density dashboard; reserved for future page-level breaks |

Exceptions: interactive controls and whole-row links have a 44px minimum target; the desktop table uses 12px vertical cell padding to preserve operating density.

## Typography

Use exactly these four sizes and two weights. Numbers and timestamps use tabular numerals.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.5 |
| Label | 14px | 600 | 1.35 |
| Heading | 20px | 600 | 1.2 |
| Display | 28px | 600 | 1.2 |

Patient names and risk values use Heading; the page title uses Display; column headings, metadata labels, warning labels, and buttons use Label. Do not use all caps for more than the existing small prototype/context label.

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#f4f7f3` | Solid page background and low-emphasis regions |
| Secondary (30%) | `#ffffff` | Table/card surfaces, product bar, and status containers |
| Accent (10%) | `#0d665d` | Primary `Open patient` action, selected/focused data-control state, wordmark mark, and available-risk label emphasis only |
| Destructive | `#9b2c2c` | Destructive action or blocking error only; not used to encode risk level |

Supporting semantic colors: use the existing focus amber `#f1b54b` only for keyboard focus, and a warning foreground/background with at least 4.5:1 text contrast only for explicit stale/missing/data-quality messages. Every semantic state includes a visible text label.

Accent reserved for: TwinBean wordmark mark, `Open patient` primary controls, keyboard-focus treatment, selected control state, and the label of an available forecast. It is never a gradient, a full risk row fill, an unavailable-risk treatment, or a substitute for status text.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | Open patient |
| Empty state heading | No monitored patients available |
| Empty state body | No synthetic patients are in the active cohort. Refresh the dashboard or ask the prototype administrator to confirm the cohort. |
| Error state | Patient dashboard could not be loaded. Check the backend connection and retry. |
| Unauthorized state | Doctor access is required. Sign out and sign in with an approved doctor account, then refresh the role token. |
| Unavailable risk | Risk unavailable |
| Data-quality label | Data quality warning |
| Destructive confirmation | None in this phase; signing out does not require confirmation. |

## States and Interaction Contract

| State | Required rendering and behaviour |
|-------|----------------------------------|
| Loading | Show a labelled `Loading monitored patientsâ€¦` region with static skeleton rows that mirror desktop columns or mobile cards. Preserve the page title and product bar; do not use a spinner-only view, animation, or delayed reveal. |
| Populated | Render every returned patient once in the server-provided default order and announce the count in a polite live region after refresh completes. |
| Empty | Use the documented empty-state copy, retain the product bar and `Refresh dashboard` secondary control, and do not render an empty table frame. |
| Error | Use the documented error copy inside the main region, preserve sign-out, and provide an enabled `Retry dashboard` button. Do not expose status codes, exception text, tokens, or stack traces. |
| Unauthorized or expired | Remove patient list content, show the documented unauthorized copy, retain sign-out, and offer the existing `Refresh role token` then sign-in recovery path. Never show cached patient data as current after a 401 or 403. |
| Available prediction | Display a numeric percentage, `24-hour AKI risk`, and `Prediction generated` time. Render returned warnings in the Data quality region before `Open patient`. |
| Unavailable prediction | Display exact `Risk unavailable`, a visible Data quality warning/reason before `Open patient`, and no numeric, bar, threshold, or risk color. |
| Missing or stale data | Display only the trusted mapped warning/reason returned for that patient in the Data quality region; do not infer freshness from the client clock or collapse it into a generic low-risk label. |
| One patient | Use `1 monitored patient` in the count and one complete row/card without leaving a visually misleading blank list area. |
| Many patients | The table/list scrolls vertically with a stable header and no nested horizontal scrolling. Keep the page performant for the backend maximum of 100 items. |
| Long content | Patient names wrap to two lines then ellipsize with an accessible full name; warning text wraps without truncation; timestamps use a two-line date/time treatment if needed. No tooltips carry essential content. |

### Navigation, keyboard, and focus

- `Open patient` is a native link when it changes route; its accessible name is `Open patient {display name}`. Whole-row navigation is optional, but it must not create nested interactive controls.
- Tab order is: skip link, product-bar actions, refresh/retry control, each patient navigation control in server order, then footer. Do not place an unfocusable row between focusable controls.
- Provide a visible `Skip to patient list` link that becomes visible on focus and moves to the main list heading.
- All controls have a 44px minimum pointer target, clear hover and active states, `:focus-visible` 3px `--focus` outline, and no color-only indication.
- Retrying preserves the current selected/focused control where possible; route navigation sets focus to the destination page heading. Keyboard-triggered refresh, open, and focus movement are immediate.

### Motion

- Operate-mode values: variance 3; motion 2; density 6.
- Only controls may transition `background-color`, `border-color`, and `transform` for 120â€“160ms with `ease-out`; press feedback may scale to 0.98.
- Do not animate list ordering, risk values, skeleton shimmer, keyboard actions, loading completion, warnings, error recovery, or navigation.
- Under `prefers-reduced-motion: reduce`, remove all transitions and transforms, including the press scale. Motion must never postpone information or change clinical interpretation.

## UI Considerations

Applicable state considerations resolved: 8 covered, 2 backstop, 0 unresolved.

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| empty | Dashboard list-collection | âœ… covered | Empty active cohort renders the documented empty heading, recovery body, and refresh control rather than an empty table. |
| loading | Dashboard list-collection and refresh control | âœ… covered | Loading renders static layout-matched skeletons and an accessible loading label without blocking product-bar access. |
| error | Dashboard list-collection, retry control, and protected navigation | âœ… covered | Failure uses documented error or unauthorized copy with the explicit retry or sign-in/role-refresh path. |
| populated | Desktop table and mobile patient-card list | âœ… covered | Every returned active-cohort patient renders once in backend-provided order with separate rule, future-risk, timestamp, warning, and navigation regions. |
| partial | Prediction and clinical-rule cells | âœ… covered | Unavailable predictions retain exact label and trusted warning/reason without a number; missing rule context uses the explicit `Insufficient creatinine history` status. |
| overflow | Table/list, product bar, patient metadata, warning text | ðŸ§ª backstop | Desktop 1440px and mobile 390px visual checks prove no horizontal document or component overflow with long names and warnings. |
| zero-one-many | Dashboard list-collection | âœ… covered | Zero, singular, and many patient counts each have prescribed copy and layout behaviour. |
| long-text | Names, timestamps, warnings, buttons, and product-bar identity | ðŸ§ª backstop | Long names, warning text, and account identity are wrapped or ellipsized to the stated rule and verified in a held-out visual state. |

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| None | none | No shadcn installation and no third-party registry declared; registry vetting is not applicable. |

## Verification Requirements

- Add a component/API test covering signed-in doctor request headers, 401/403 recovery, all-patient rendering, server order preservation, available percentage/timestamp, and exact `Risk unavailable` without a numeric fallback.
- Add fixture cases for valid forecast, unavailable forecast, missing-data warning, stale-data warning, empty active cohort, network failure, long patient name, and long warning copy. Use synthetic data only.
- Verify a 1440px desktop table and 390px mobile card view have no horizontal document or inspected-component overflow, extending the existing `verify:layout` harness.
- Test keyboard focus visibility, skip link, 44px targets, link names, and reduced-motion behaviour. Use text assertions for every status; color alone cannot satisfy a test.
- Assert that the dashboard consumes a bounded aggregate response and never performs client-side N+1 requests to obtain per-patient rule/prediction summaries.

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS
- [ ] Dimension 7 Inventory Provenance: PASS â€” not applicable because Tool: none

**Approval:** pending
