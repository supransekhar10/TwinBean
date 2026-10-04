---
schema_version: 1
open_count: 0
waived_count: 0
fixed_count: 2
total_count: 2
last_updated: 2026-10-04T13:59:39.275Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | deviation | backend/app/clinical_rules.py |  | Filtered non-creatinine events before sorting rule evidence. | fixed |  | 2026-10-04T13:21:20.022Z | 2026-10-04T13:21:38.571Z |
| 2 | 03 | deviation | backend/app/aki_model.py |  | Validated nested cohort and partition manifest metadata before deserialization. | fixed |  | 2026-10-04T13:59:18.787Z | 2026-10-04T13:59:39.275Z |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "03",
    "file": "backend/app/clinical_rules.py",
    "line": null,
    "description": "Filtered non-creatinine events before sorting rule evidence.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-04T13:21:20.022Z",
    "resolved_at": "2026-10-04T13:21:38.571Z",
    "milestone": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "03",
    "file": "backend/app/aki_model.py",
    "line": null,
    "description": "Validated nested cohort and partition manifest metadata before deserialization.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-04T13:59:18.787Z",
    "resolved_at": "2026-10-04T13:59:39.275Z",
    "milestone": null
  }
]
````
