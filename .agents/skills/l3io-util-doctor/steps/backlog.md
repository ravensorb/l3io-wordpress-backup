## Backlog Mode

Invoked with `backlog` argument. Read-only — lists all items in the consolidated `backlog:` list from the issues file in a readable table grouped by severity. No files are changed.

### Steps

**Step BL1 — Load config and resolve the issues file**

Load config (same as layout cleanup). The backlog lives in `{pm_issues_file}`
(`{pm_state_root}/issues.yaml`) — the single flat deferred-issue list the current layout
uses, written by `pm-status.py append-issue`. If it does not exist, decide which case this is
using the layout detection from Check 2b:

- **A legacy layout is present** (legacy flat `sprint-status*.yaml`, or legacy per-epic
  `_bmad/state/`):
  ```
  No issues file at {pm_issues_file} — this project is still on a legacy state layout.
  Run /l3io-util-doctor migrate-state to migrate; the backlog is carried over as part of it.
  ```
- **The sharded tree exists but has no issues file yet**, or nothing exists at all:
  ```
  Backlog is empty — no issues file at {pm_issues_file} yet. It is created the first time a
  review defers an item.
  ```

Exit in either case.

**Step BL2 — Read**

```bash
uv run {pm_status} list-issues --state-root {pm_state_root} --format json
```

If the list is empty, print `Backlog is empty — no open items.` and exit.

**Step BL3 — Print table**

Group items by severity (Critical → High → Medium → Low → unknown); within a group, sort by
`epic` then `key`. `scheduled` items show their story; `origin_archived` items are marked.

```
BACKLOG — {pm_issues_file}
================================================================
Sev    Key           Epic  Sprint  Status              Title
----------------------------------------------------------------
High
  HIGH   BL-E001-002   001   —       scheduled E003-S02-004  {title}
Low
  LOW    BL-E002-001   002   03      backlog (archived)      {title}
================================================================
Open: {n}  (untriaged {u} · scheduled {s} · origin archived {o})
Run /l3io-util-doctor triage to audit these and close what is already fixed.
```

Truncate titles at 50 characters with `…`. Show the sprint as `—` when blank.

---
